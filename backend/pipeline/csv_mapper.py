"""
csv_mapper.py
증권사별 제각각인 거래내역 CSV/엑셀을 LLM 매핑표로 Trade 스키마에 맞춰 변환.

역할 분담(설계 원칙): LLM(제미나이)은 "매핑표"를 만들 뿐이고, 실제 데이터 변환은
pandas 코드가 결정론적으로 수행한다. 거래 데이터 전체를 LLM에 보내지 않는 이유:
(1) 원거래내역의 외부 전송 최소화, (2) 숫자가 조용히 바뀌는 환각 위험 차단,
(3) 비용·속도.

LLM 호출은 2패스:
  패스 1  파일 앞 15줄 원문 → {header_row(헤더 줄 번호 — 증권사 파일은 머리에
          계좌 요약이 붙곤 함), columns(원본 컬럼명→Trade 필드), date_format}
  패스 2  전체 파일에서 뽑은 거래구분 고유값 목록 → {원본 값: 매수|매도|null}.
          앞 15줄 샘플에는 없던 값이 뒤에 나올 수 있어, 값 매핑만은 전체
          고유값(외부로 나가는 건 값 몇 개뿐)으로 다시 묻는다. null = 거래가
          아닌 행(입출금·배당 등)으로 버림.

검증: 매핑표가 엉터리일 가능성을 코드가 방어한다 — 필수 필드 존재, 날짜 전부
파싱, 수량·단가 양수, 거래구분 정규화 완료, 행 수 보존(변환 + 버림 = 원본).
하나라도 실패하면 MappingError — 부분 저장 없음(전부 아니면 전무).

실패 정책: 호출부(worker)가 MappingError를 받아 job을 실패 처리한다.
"""

import io
import json
import logging
import os

import pandas as pd

logger = logging.getLogger(__name__)

GEMINI_MODEL = "gemini-3.1-flash-lite"
HEAD_LINES = 15  # LLM에 보여주는 파일 앞부분 (헤더 탐지 + 컬럼 매핑용)

# Trade 테이블(orm.Trade) 필드 — 저장 대상 스키마
FIELDS_ALL = ["거래일자", "종목명", "거래구분", "거래수량", "거래단가",
              "거래금액", "수수료", "거래세", "정산금액"]
FIELDS_REQUIRED = ["거래일자", "종목명", "거래구분", "거래수량", "거래단가"]
_NUMERIC_FIELDS = ["거래수량", "거래단가", "거래금액", "수수료", "거래세", "정산금액"]


class MappingError(Exception):
    """매핑 불가·검증 실패 — 저장하지 않고 job 실패 처리해야 하는 오류."""


# ─ LLM 호출부 (테스트에서 대체하는 이음새 · 모델 교체 지점) ─

def _call_llm(prompt: str) -> str:
    from pathlib import Path

    from dotenv import load_dotenv
    from google import genai

    # .env 로드는 여기(실호출 시점)에서만 — 모듈 import 시점에 하면 테스트
    # 수집 단계에서 .env의 DATABASE_URL이 환경에 들어가 테스트 DB 격리가 깨진다.
    # 경로 명시: .env는 backend/에 있는데 CWD는 실행 방식마다 달라서
    # (레포 루트 pytest vs backend에서 uvicorn) 기본 탐색에 맡기지 않는다.
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    response = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
    return response.text


def _parse_json(text: str) -> dict:
    """LLM 응답에서 JSON 추출 — 마크다운 코드펜스로 감싸는 습성 방어."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]
    return json.loads(text)


def _ask(prompt: str) -> dict:
    """LLM에 JSON 응답을 요청 — 실패(호출·파싱) 시 1회 재시도 후 MappingError."""
    last = None
    for _ in range(2):
        try:
            return _parse_json(_call_llm(prompt))
        except Exception as e:  # noqa: BLE001 — 원인 무관하게 재시도 1회
            last = e
    raise MappingError(f"LLM 매핑 응답 실패: {last!r}")


# ─ 패스 1: 헤더 위치 + 컬럼 매핑 ─

def get_mapping(head_text: str) -> dict:
    numbered = "\n".join(
        f"{i}: {line}" for i, line in enumerate(head_text.splitlines())
    )
    prompt = f"""다음은 증권사 거래내역 파일의 첫 부분입니다 (형식: 줄번호: 내용):

{numbered}

이 파일을 표준 스키마로 변환하기 위한 매핑 정보가 필요합니다.

표준 필드 (의미):
- 거래일자: 거래(체결) 날짜
- 종목명: 종목 이름
- 거래구분: 매수/매도 구분
- 거래수량: 체결 수량
- 거래단가: 체결 단가(1주당 가격)
- 거래금액: 총 거래대금
- 수수료: 수수료
- 거래세: 세금
- 정산금액: 정산(수수료·세금 반영) 금액

반드시 아래 JSON 형식으로만 답하세요. 다른 텍스트 없이 JSON만:
{{
  "header_row": <컬럼명들이 있는 줄 번호(0부터 셈)>,
  "columns": {{"<원본 컬럼명>": "<표준 필드명>", ...}},
  "date_format": "<날짜 형식, 예: %Y/%m/%d. 불확실하면 null>"
}}

규칙: columns에는 대응하는 표준 필드가 있는 원본 컬럼만 넣으세요. 같은 표준
필드에 두 컬럼을 매핑하지 마세요."""
    mapping = _ask(prompt)
    _check_mapping_shape(mapping)
    return mapping


def _check_mapping_shape(mapping: dict) -> None:
    if not isinstance(mapping.get("header_row"), int) or mapping["header_row"] < 0:
        raise MappingError(f"매핑표 header_row 이상: {mapping.get('header_row')!r}")
    columns = mapping.get("columns")
    if not isinstance(columns, dict) or not columns:
        raise MappingError("매핑표 columns 없음")
    targets = [t for t in columns.values() if t]
    bad = [t for t in targets if t not in FIELDS_ALL]
    if bad:
        raise MappingError(f"매핑표에 모르는 표준 필드: {bad}")
    dup = {t for t in targets if targets.count(t) > 1}
    if dup:
        raise MappingError(f"표준 필드에 원본 컬럼이 중복 매핑됨: {sorted(dup)}")
    missing = [f for f in FIELDS_REQUIRED if f not in targets]
    if missing:
        raise MappingError(f"필수 필드 매핑 없음: {missing}")


# ─ 패스 2: 거래구분 값 매핑 (전체 고유값 기준) ─

def get_value_mapping(values: list[str]) -> dict:
    prompt = f"""증권사 거래내역의 거래구분 컬럼에 등장하는 값 목록입니다:
{json.dumps(values, ensure_ascii=False)}

각 값을 분류하세요:
- 주식을 사는 거래(현금매수, 신용매수 등) → "매수"
- 주식을 파는 거래(현금매도, 매도상환 등) → "매도"
- 주식 거래가 아닌 것(입금, 출금, 이체, 배당, 이자 등) → null

반드시 아래 JSON 형식으로만, 목록의 모든 값을 빠짐없이 포함해서 답하세요:
{{"<원본 값>": "매수" | "매도" | null, ...}}"""
    value_map = _ask(prompt)
    missing = [v for v in values if v not in value_map]
    if missing:
        raise MappingError(f"거래구분 값 매핑 누락: {missing}")
    bad = {v: t for v, t in value_map.items() if t not in ("매수", "매도", None)}
    if bad:
        raise MappingError(f"거래구분 매핑 값 이상: {bad}")
    return value_map


# ─ 파일 읽기 ─

def _decode(raw: bytes) -> str:
    """국내 증권사 CSV 인코딩 대응 — utf-8(-sig) 우선, 실패 시 cp949."""
    for enc in ("utf-8-sig", "cp949"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    raise MappingError("파일 인코딩 인식 불가 (utf-8/cp949 아님)")


def _is_excel(filename: str) -> bool:
    return filename.lower().endswith((".xlsx", ".xls"))


def _is_html(raw: bytes) -> bool:
    """확장자가 아니라 내용으로 판별 — 국내 증권사 '.xls' 내보내기는 실제로는
    HTML 문서인 경우가 많다(키움 등)."""
    head = raw[:2000].lstrip()
    return head[:1].startswith(b"<") or b"<html" in head.lower() or b"<table" in head.lower()


def _load_html_grid(raw: bytes) -> pd.DataFrame:
    """HTML 문서에서 가장 큰 표를 헤더 없는 격자로 추출.

    인코딩은 read_html의 추정에 맡기지 않고 _decode로 직접 판별해 넘긴다
    (charset 메타 없는 파일에서 한글이 깨지는 실측 문제)."""
    tables = pd.read_html(io.StringIO(_decode(raw)), header=None)
    if not tables:
        raise MappingError("HTML에서 표를 찾지 못함")
    return max(tables, key=lambda t: t.size).reset_index(drop=True)


def _load_grid(raw: bytes, filename: str) -> pd.DataFrame | None:
    """엑셀·HTML을 헤더 없는 격자로 반환. CSV(텍스트)는 None — 텍스트 경로 사용."""
    if _is_html(raw):
        return _load_html_grid(raw)
    if _is_excel(filename):
        return pd.read_excel(io.BytesIO(raw), header=None)
    return None


def _read_head(raw: bytes, filename: str) -> str:
    """LLM 패스 1에 보여줄 파일 앞부분 텍스트."""
    grid = _load_grid(raw, filename)
    if grid is not None:
        return grid.head(HEAD_LINES).to_csv(index=False, header=False)
    lines = _decode(raw).splitlines()[:HEAD_LINES]
    return "\n".join(lines)


def _read_table(raw: bytes, filename: str, header_row: int) -> pd.DataFrame:
    grid = _load_grid(raw, filename)
    if grid is not None:
        # 격자에서 header_row 줄을 컬럼명으로, 그 아래를 데이터로
        if header_row >= len(grid):
            raise MappingError(f"header_row({header_row})가 표 범위 밖")
        df = grid.iloc[header_row + 1:].reset_index(drop=True)
        df.columns = [str(c).strip() for c in grid.iloc[header_row]]
    else:
        # skip_blank_lines=False: 빈 줄도 줄 번호에 포함시켜, LLM이 본 원문
        # 줄 번호(header_row)와 pandas의 셈이 어긋나지 않게 한다
        df = pd.read_csv(io.StringIO(_decode(raw)), header=header_row,
                         skip_blank_lines=False)
        df.columns = [str(c).strip() for c in df.columns]
    return df.dropna(how="all").reset_index(drop=True)  # 완전 빈 줄 제거


# ─ 결정론적 변환 (LLM 무관) ─

def apply_mapping(df: pd.DataFrame, mapping: dict, value_map: dict):
    """매핑표 적용 → (Trade 스키마 DataFrame, 버린 비거래 행 수).

    버림은 거래구분이 null로 매핑된 행(입출금 등)뿐 — 그 외 어떤 행도 조용히
    사라지지 않는다(validate가 행 수 보존을 검사).
    """
    rename = {src: dst for src, dst in mapping["columns"].items()
              if dst and src in df.columns}
    got = set(rename.values())
    missing = [f for f in FIELDS_REQUIRED if f not in got]
    if missing:  # 매핑표의 원본 컬럼명이 실제 파일에 없음 (헤더 줄 오인 등)
        raise MappingError(f"매핑된 원본 컬럼이 파일에 없음 — 필수 필드 누락: {missing}")
    out = df.rename(columns=rename)[list(got)].copy()

    # 거래구분 정규화 + 비거래 행 버림
    raw_kind = out["거래구분"].astype(str).str.strip()
    unknown = sorted(set(raw_kind) - set(value_map))
    if unknown:
        raise MappingError(f"거래구분 값 매핑에 없는 값: {unknown}")
    kind = raw_kind.map(value_map)
    keep = kind.notna()
    n_dropped = int((~keep).sum())
    out = out[keep].copy()
    out["거래구분"] = kind[keep]

    # 날짜: 매핑표의 형식 힌트 우선, 실패하면 자동 추정
    fmt = mapping.get("date_format") or None
    dates = None
    if fmt:
        try:
            dates = pd.to_datetime(out["거래일자"].astype(str).str.strip(),
                                   format=fmt, errors="raise")
        except (ValueError, TypeError):
            dates = None
    if dates is None:
        dates = pd.to_datetime(out["거래일자"].astype(str).str.strip(),
                               errors="coerce")
    out["거래일자"] = dates

    # 숫자: 콤마·공백 제거 후 변환 (실패값은 NaN → validate가 잡음)
    for col in _NUMERIC_FIELDS:
        if col in out.columns:
            out[col] = pd.to_numeric(
                out[col].astype(str).str.replace(",", "").str.strip(),
                errors="coerce",
            )

    # 없는 필드 기본값 (Trade 테이블이 NOT NULL)
    if "거래금액" not in out.columns:
        out["거래금액"] = out["거래수량"] * out["거래단가"]
    for col in ("수수료", "거래세"):
        if col not in out.columns:
            out[col] = 0
    if "정산금액" not in out.columns:
        out["정산금액"] = out["거래금액"]

    return out[FIELDS_ALL].reset_index(drop=True), n_dropped


def validate(out: pd.DataFrame, n_source_rows: int, n_dropped: int) -> None:
    """변환 결과 검증 — 매핑표가 엉터리였을 가능성을 저장 전에 차단."""
    if len(out) == 0:
        raise MappingError("변환 결과가 빈 데이터 (거래 행 없음)")
    if len(out) + n_dropped != n_source_rows:
        raise MappingError(
            f"행 수 불일치: 원본 {n_source_rows} != 변환 {len(out)} + 버림 {n_dropped}")

    bad_dates = int(out["거래일자"].isna().sum())
    if bad_dates:
        raise MappingError(f"날짜 파싱 실패 {bad_dates}행 — 거래일자 매핑 의심")
    for col, positive in (("거래수량", True), ("거래단가", True), ("거래금액", False)):
        n_nan = int(out[col].isna().sum())
        if n_nan:
            raise MappingError(f"{col} 숫자 변환 실패 {n_nan}행")
        if positive and int((out[col] <= 0).sum()):
            raise MappingError(f"{col}에 0 이하 값 존재 — 매핑 의심")
    if out["종목명"].isna().any() or (out["종목명"].astype(str).str.strip() == "").any():
        raise MappingError("종목명 빈 값 존재")
    kinds = set(out["거래구분"].unique())
    if not kinds <= {"매수", "매도"}:
        raise MappingError(f"거래구분 정규화 실패: {kinds - {'매수', '매도'}}")


# ─ 오케스트레이터 (worker가 부르는 진입점) ─

def map_file(raw: bytes, filename: str) -> pd.DataFrame:
    """파일 원본 → Trade 스키마 DataFrame (거래일자는 datetime, 행은 파일 순서).

    실패는 전부 MappingError로 승격 — 호출부는 이것 하나만 처리하면 된다.
    """
    try:
        mapping = get_mapping(_read_head(raw, filename))
        df = _read_table(raw, filename, mapping["header_row"])

        kind_col = next(src for src, dst in mapping["columns"].items()
                        if dst == "거래구분")
        if kind_col not in df.columns:
            raise MappingError(f"거래구분 컬럼({kind_col!r})이 파일에 없음 — 헤더 줄 오인 의심")
        values = sorted(df[kind_col].dropna().astype(str).str.strip().unique())
        value_map = get_value_mapping(values)

        out, n_dropped = apply_mapping(df, mapping, value_map)
        validate(out, len(df), n_dropped)
        logger.info("CSV 매핑 완료: %s — 거래 %d행 (비거래 %d행 버림)",
                    filename, len(out), n_dropped)
        return out
    except MappingError:
        raise
    except Exception as e:  # noqa: BLE001 — 예상 밖 오류도 저장 없이 실패 처리
        raise MappingError(f"매핑 중 오류: {e!r}") from e
