"""
CSV 매핑 검증 — LLM(제미나이)은 가짜로 대체, 네트워크 0.

계약: map_file(원본 bytes, 파일명) → Trade 스키마 DataFrame.
LLM은 매핑표만 만들고 변환은 코드가 한다 — 여기서 고정하는 것은 (1) 매핑표가
올바를 때 변환·기본값·비거래 행 버림이 정확한가, (2) 매핑표가 엉터리일 때
저장 전에 MappingError로 막히는가.
"""

import io
import json

import pandas as pd
import pytest

from pipeline import csv_mapper
from pipeline.csv_mapper import (
    MappingError,
    apply_mapping,
    get_mapping,
    map_file,
    validate,
)


def fake_llm(monkeypatch, responses: list):
    """_call_llm을 대체 — 호출 순서대로 responses를 반환(Exception이면 raise)."""
    calls = []

    def _fake(prompt: str) -> str:
        idx = min(len(calls), len(responses) - 1)
        calls.append(prompt)
        r = responses[idx]
        if isinstance(r, Exception):
            raise r
        return r

    monkeypatch.setattr(csv_mapper, "_call_llm", _fake)
    return calls


def j(obj) -> str:
    return json.dumps(obj, ensure_ascii=False)


# ─ 픽스처 1: 컬럼명만 다른 단순 CSV ─

CSV_SIMPLE = (
    "매매일자,종목,구분,수량,단가,거래대금\n"
    "2026-01-05,삼성전자,매수,10,60000,600000\n"
    "2026-01-07,카카오,매도,5,45000,225000\n"
).encode("utf-8")

MAP_SIMPLE = {
    "header_row": 0,
    "columns": {"매매일자": "거래일자", "종목": "종목명", "구분": "거래구분",
                "수량": "거래수량", "단가": "거래단가", "거래대금": "거래금액"},
    "date_format": "%Y-%m-%d",
}
VALUES_SIMPLE = {"매수": "매수", "매도": "매도"}


def test_simple_rename_and_defaults(monkeypatch):
    fake_llm(monkeypatch, [j(MAP_SIMPLE), j(VALUES_SIMPLE)])
    out = map_file(CSV_SIMPLE, "kiwoom.csv")

    assert list(out.columns) == csv_mapper.FIELDS_ALL
    assert len(out) == 2
    assert out.loc[0, "거래일자"] == pd.Timestamp("2026-01-05")
    assert out.loc[0, "종목명"] == "삼성전자"
    assert out.loc[0, "거래구분"] == "매수"
    assert out.loc[0, "거래수량"] == 10
    assert out.loc[0, "거래단가"] == 60000
    assert out.loc[0, "거래금액"] == 600000
    # 파일에 없는 필드의 기본값
    assert (out["수수료"] == 0).all() and (out["거래세"] == 0).all()
    assert (out["정산금액"] == out["거래금액"]).all()


# ─ 픽스처 2: 머리말 + 빈 줄 + 슬래시 날짜 + cp949 인코딩 ─

CSV_PREAMBLE = (
    "계좌번호: 123-45-678900\n"
    "조회기간: 2026.01.01 ~ 2026.03.31\n"
    "\n"
    "체결일자,종목명,매매구분,체결수량,체결단가\n"
    "2026/01/05,현대차,현금매수,3,200000\n"
    "2026/02/10,현대차,현금매도,3,210000\n"
).encode("cp949")

MAP_PREAMBLE = {
    "header_row": 3,  # 빈 줄 포함 물리적 줄 번호 — LLM이 보는 원문 기준
    "columns": {"체결일자": "거래일자", "종목명": "종목명", "매매구분": "거래구분",
                "체결수량": "거래수량", "체결단가": "거래단가"},
    "date_format": "%Y/%m/%d",
}


def test_preamble_blank_line_and_cp949(monkeypatch):
    fake_llm(monkeypatch, [
        j(MAP_PREAMBLE),
        j({"현금매수": "매수", "현금매도": "매도"}),
    ])
    out = map_file(CSV_PREAMBLE, "samsung.csv")

    assert len(out) == 2
    assert out.loc[0, "거래일자"] == pd.Timestamp("2026-01-05")
    assert list(out["거래구분"]) == ["매수", "매도"]
    assert out.loc[1, "거래단가"] == 210000
    # 거래금액 미제공 → 수량×단가
    assert out.loc[0, "거래금액"] == 3 * 200000


# ─ 픽스처 3: 입출금 행 + 콤마 수량 ─

CSV_DEPOSIT = (
    '거래일,종목명,거래유형,거래수량,거래단가,수수료\n'
    '2026-03-02,NAVER,매수,"1,000",180000,150\n'
    '2026-03-05,,은행이체입금,,,\n'
    '2026-03-09,NAVER,매도,"1,000",190000,150\n'
).encode("utf-8")

MAP_DEPOSIT = {
    "header_row": 0,
    "columns": {"거래일": "거래일자", "종목명": "종목명", "거래유형": "거래구분",
                "거래수량": "거래수량", "거래단가": "거래단가", "수수료": "수수료"},
    "date_format": None,
}


def test_nontrade_rows_dropped_and_commas_parsed(monkeypatch):
    calls = fake_llm(monkeypatch, [
        j(MAP_DEPOSIT),
        j({"매수": "매수", "매도": "매도", "은행이체입금": None}),
    ])
    out = map_file(CSV_DEPOSIT, "mirae.csv")

    assert len(out) == 2  # 입금 행은 버려짐
    assert (out["종목명"] == "NAVER").all()
    assert (out["거래수량"] == 1000).all()  # "1,000" → 1000
    assert (out["수수료"] == 150).all()
    # 패스 2 프롬프트에는 전체 고유값이 들어감
    assert "은행이체입금" in calls[1]


# ─ LLM에 나가는 내용의 경계 ─

def test_llm_sees_only_head_lines(monkeypatch):
    """패스 1에 파일 앞 HEAD_LINES줄만 나감 — 원거래 전체 미전송 보증."""
    many_rows = "매매일자,종목,구분,수량,단가,거래대금\n" + "\n".join(
        f"2026-01-{d:02d},종목{d},매수,1,1000,1000" for d in range(1, 28)
    )
    fake_calls = fake_llm(monkeypatch, [j(MAP_SIMPLE), j({"매수": "매수"})])
    map_file(many_rows.encode("utf-8"), "big.csv")

    head_prompt = fake_calls[0]
    assert "종목14" in head_prompt      # 15줄째(헤더+14행)까지는 보임
    assert "종목15" not in head_prompt  # 그 뒤는 안 나감
    assert "종목27" not in head_prompt


# ─ 개인정보 마스킹 — LLM에 나가는 head에서 식별자 값만 가려지는가 ─

def test_mask_pii_hides_identifiers_keeps_structure():
    head = (
        "계좌번호: 123-45-678900  예금주: 홍길동\n"
        "연락처: 010-1234-5678  이메일: hong@test.com  주민번호 900101-1234567\n"
        "예수금: 5,000,000  잔고 12345678901\n"
        "체결일자,종목명,매매구분,체결수량,체결단가,예수금\n"
        "2026/01/05,현대차,현금매수,3,200000,100000\n"
    )
    out = csv_mapper._mask_pii(head)
    for pii in ("123-45-678900", "홍길동", "010-1234-5678", "hong@test.com",
                "900101-1234567", "5,000,000", "12345678901"):
        assert pii not in out
    # 구조는 유지 — 키워드·헤더 줄·데이터 행은 그대로 (컬럼명 "예수금" 포함)
    assert "계좌번호:" in out and "예수금:" in out
    assert "체결일자,종목명,매매구분,체결수량,체결단가,예수금" in out
    assert "2026/01/05,현대차,현금매수,3,200000,100000" in out


def test_mask_pii_preserves_dates():
    text = "2026-01-05\n2026/01/05\n2026.1.5\n20260105\n체결 20260105 종가"
    assert csv_mapper._mask_pii(text) == text


def test_llm_prompt_is_masked(monkeypatch):
    """전송 직전 프롬프트 기준 검증 — 계좌 요약이 붙은 실제 흐름."""
    fake_calls = fake_llm(monkeypatch, [
        j(MAP_PREAMBLE), j({"현금매수": "매수", "현금매도": "매도"})])
    map_file(CSV_PREAMBLE, "samsung.csv")
    head_prompt = fake_calls[0]
    assert "123-45-678900" not in head_prompt   # 계좌번호 가림
    assert "계좌번호:" in head_prompt            # 키워드(구조)는 남음
    assert "2026/01/05" in head_prompt           # 날짜 샘플은 원형


# ─ 매핑표가 엉터리일 때 — 저장 전에 막히는가 ─

def test_mapping_missing_required_field(monkeypatch):
    bad = {**MAP_SIMPLE,
           "columns": {k: v for k, v in MAP_SIMPLE["columns"].items()
                       if v != "거래수량"}}
    fake_llm(monkeypatch, [j(bad)])
    with pytest.raises(MappingError, match="필수 필드"):
        get_mapping("아무 텍스트")


def test_mapping_duplicate_target(monkeypatch):
    bad = {**MAP_SIMPLE,
           "columns": {**MAP_SIMPLE["columns"], "단가2": "거래단가"}}
    fake_llm(monkeypatch, [j(bad)])
    with pytest.raises(MappingError, match="중복"):
        get_mapping("아무 텍스트")


def test_mapping_unknown_target_field(monkeypatch):
    bad = {**MAP_SIMPLE, "columns": {**MAP_SIMPLE["columns"], "비고": "메모"}}
    fake_llm(monkeypatch, [j(bad)])
    with pytest.raises(MappingError, match="모르는"):
        get_mapping("아무 텍스트")


def test_wrong_date_mapping_caught_by_validate():
    """날짜 필드에 금액 컬럼을 매핑한 엉터리 매핑표 — 날짜 파싱 실패로 차단.

    (단가 같은 순수 숫자 컬럼은 pandas가 타임스탬프로도 읽을 수 있어, 숫자가
    아닌 값이 섞인 컬럼을 날짜에 잘못 매핑한 경우로 검증한다.)
    """
    df = pd.read_csv(io.BytesIO(CSV_SIMPLE))
    wrong = {"header_row": 0, "date_format": None,
             "columns": {"구분": "거래일자",       # 매수/매도를 날짜로 (오매핑)
                         "종목": "종목명", "매매일자": "거래구분",
                         "수량": "거래수량", "단가": "거래단가"}}
    value_map = {"2026-01-05": "매수", "2026-01-07": "매도"}
    out, dropped = apply_mapping(df, wrong, value_map)
    with pytest.raises(MappingError, match="날짜 파싱 실패"):
        validate(out, len(df), dropped)


def test_unknown_kind_value_rejected():
    df = pd.read_csv(io.BytesIO(CSV_SIMPLE))
    with pytest.raises(MappingError, match="없는 값"):
        apply_mapping(df, MAP_SIMPLE, {"매수": "매수"})  # "매도" 누락


def test_value_mapping_must_cover_all(monkeypatch):
    fake_llm(monkeypatch, [j({"매수": "매수"})])  # "매도" 빠뜨림
    with pytest.raises(MappingError, match="누락"):
        csv_mapper.get_value_mapping(["매수", "매도"])


def test_row_count_invariant():
    df = pd.read_csv(io.BytesIO(CSV_SIMPLE))
    out, dropped = apply_mapping(df, MAP_SIMPLE, VALUES_SIMPLE)
    with pytest.raises(MappingError, match="행 수 불일치"):
        validate(out, len(df) + 1, dropped)  # 원본이 1행 더 많았다고 가정


def test_all_rows_nontrade_is_error(monkeypatch):
    """전 행이 입출금이면 빈 결과 — 저장 대신 실패."""
    csv = (
        "거래일,종목명,거래유형,거래수량,거래단가\n"
        "2026-03-05,,입금,,\n"
    ).encode("utf-8")
    fake_llm(monkeypatch, [
        j({**MAP_DEPOSIT, "columns": {k: v for k, v in MAP_DEPOSIT["columns"].items()
                                      if k != "수수료"}}),
        j({"입금": None}),
    ])
    with pytest.raises(MappingError, match="빈 데이터"):
        map_file(csv, "empty.csv")


# ─ LLM 호출 실패 정책 ─

def test_llm_retry_once_then_success(monkeypatch):
    fake_llm(monkeypatch, [RuntimeError("일시 오류"), j(MAP_SIMPLE),
                           j(VALUES_SIMPLE)])
    out = map_file(CSV_SIMPLE, "retry.csv")
    assert len(out) == 2


def test_llm_two_failures_is_mapping_error(monkeypatch):
    fake_llm(monkeypatch, [RuntimeError("죽음"), RuntimeError("또 죽음")])
    with pytest.raises(MappingError, match="LLM"):
        map_file(CSV_SIMPLE, "dead.csv")


def test_markdown_fenced_json_accepted(monkeypatch):
    """LLM이 ```json 펜스로 감싸 답해도 파싱된다."""
    fenced = "```json\n" + j(MAP_SIMPLE) + "\n```"
    fake_llm(monkeypatch, [fenced, j(VALUES_SIMPLE)])
    out = map_file(CSV_SIMPLE, "fenced.csv")
    assert len(out) == 2


# ─ HTML 위장 엑셀 (키움 등 국내 증권사 .xls 내보내기의 실제 형식) ─

HTML_XLS = """
<html><body><table>
<tr><td colspan="4">[키움증권]주식 거래내역</td></tr>
<tr><td>거래일자</td><td>종목명</td><td>거래구분</td><td>거래수량</td><td>거래단가</td></tr>
<tr><td>2025.08.20</td><td>삼성전자</td><td>배당금입금</td><td></td><td>0</td></tr>
<tr><td>2025.09.01</td><td>삼성전자</td><td>매수</td><td>10</td><td>70,000</td></tr>
<tr><td>2025.09.15</td><td>삼성전자</td><td>매도</td><td>10</td><td>75,000</td></tr>
</table></body></html>
""".encode("utf-8")

MAP_HTML = {
    "header_row": 1,  # 0행은 제목(colspan)
    "columns": {"거래일자": "거래일자", "종목명": "종목명", "거래구분": "거래구분",
                "거래수량": "거래수량", "거래단가": "거래단가"},
    "date_format": "%Y.%m.%d",
}


def test_html_disguised_as_xls(monkeypatch):
    """확장자는 .xls지만 내용이 HTML인 파일 — 내용 기반 판별로 표 추출."""
    fake_llm(monkeypatch, [
        j(MAP_HTML),
        j({"배당금입금": None, "매수": "매수", "매도": "매도"}),
    ])
    out = map_file(HTML_XLS, "거래내역.xls")

    assert len(out) == 2  # 배당 행은 버려짐
    assert list(out["거래구분"]) == ["매수", "매도"]
    assert out.loc[0, "거래일자"] == pd.Timestamp("2025-09-01")
    assert out.loc[1, "거래단가"] == 75000
    assert out.loc[1, "거래금액"] == 10 * 75000


# ─ 엑셀 ─

def test_excel_roundtrip(monkeypatch, tmp_path):
    df = pd.DataFrame({
        "매매일자": ["2026-01-05", "2026-01-07"],
        "종목": ["삼성전자", "카카오"],
        "구분": ["매수", "매도"],
        "수량": [10, 5],
        "단가": [60000, 45000],
        "거래대금": [600000, 225000],
    })
    path = tmp_path / "trades.xlsx"
    df.to_excel(path, index=False)

    fake_llm(monkeypatch, [j(MAP_SIMPLE), j(VALUES_SIMPLE)])
    out = map_file(path.read_bytes(), "trades.xlsx")
    assert len(out) == 2
    assert out.loc[1, "종목명"] == "카카오"
    assert out.loc[1, "거래금액"] == 225000
