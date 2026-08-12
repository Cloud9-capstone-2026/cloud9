"""
detect.py
DB(trades) 기반 계층별 탐지 — Rule-based + Z-score(+마할라노비스) + 3계층 GRU.
업로드 worker(pipeline.jobs)가 호출해 reports/*.json 저장 + AnalysisResult INSERT.

판정 방식(계층별 독립 flag + 단계형 등급 — 프론트 합의 구조):
  각 거래에 대해 계층이 각자 판정한다.
    rule  = 위반 규칙 존재 여부
    stat  = 마할라노비스 거리 > 임계(2.5, zscore 정의)
    deep  = 거래 편향 확률(4종 최댓값) >= DEEP_THRESHOLD
  verdict = flag 개수 0 → "정상", 1 → "경고", 2 이상 → "이상".
  가중합 점수는 폐기 — 캘리브레이션에서 3계층 단독이 가중합(0.3/0.3/0.4)보다
  나았고(AP 0.948 vs 0.883), 1·2계층의 가치(명백 위반·비편향 이상치)는 독립
  flag로 사는 구조가 맞다.

3계층(models.layer3)은 거래 우선(trade-first) 출력 — 이번 업로드 + 이전 업로드
전체 거래를 시퀀스 태깅 GRU에 통과시켜 새 거래 각각에 편향 귀속 확률과 주도
편향(top_bias)을 단다(이력이 길면 창 분할로 전 거래 채점). 시장 맥락 없는
거래(시세 조회 실패 — layer3가 채점 제외)·채점 전체 실패(아티팩트 부재·torch
미설치) 시 그 거래는 deep 판정 없이 두 계층만으로 같은 규칙을 적용하고
layers_available로 표시한다.
"""

import json
import re
import logging
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from models.rule_based import run_rule_based
from models.zscore import run_zscore
from pipeline.monitor import check_distribution

try:  # 3계층 — 의존성(torch)·아티팩트가 없으면 2계층으로 폴백
    from models.layer3 import score_account as layer3_score
except Exception:  # noqa: BLE001
    layer3_score = None

# backend/pipeline/detect.py → backend/
BACKEND_DIR = Path(__file__).resolve().parent.parent

logging.getLogger("pykrx").setLevel(logging.ERROR)

# DB(trades) 컬럼 → 모델이 기대하는 표준 컬럼
DB_TO_STANDARD = {
    "거래일자": "날짜",
    "거래구분": "매매구분",
    "거래수량": "체결수량",
    "거래단가": "체결단가",
    "거래금액": "총거래금액",
}

REPORTS_DIR = BACKEND_DIR / "reports"

# 3계층 flag 임계값 — ml.experiments.calibrate_ensemble의 "최약축≥0.3" 후보
# (튜닝 s11+s13: 정밀도 0.977, 4개 편향축 재현율 전부 ≥0.30 / 평가 s103·s104
#  검증: 정밀도 0.967~0.968, 재현율 0.345~0.355). 2026-08-06 확정.
DEEP_THRESHOLD = 0.7283


def _standardize(df: pd.DataFrame) -> pd.DataFrame:
    """DB/CSV 컬럼명을 모델 표준 컬럼명으로 변환 + 타입 정리."""
    df = df.rename(columns=DB_TO_STANDARD)
    df["날짜"] = pd.to_datetime(df["날짜"])
    for col in ["체결수량", "체결단가", "총거래금액"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.sort_values("날짜").reset_index(drop=True)


def _trades_to_df(trades: list) -> pd.DataFrame:
    """Trade ORM 객체 리스트 → 표준 DataFrame. 빈 리스트면 표준 컬럼만 가진 빈 DF."""
    if not trades:
        return pd.DataFrame(columns=["날짜", "종목명", "매매구분", "체결수량", "체결단가", "총거래금액"])
    rows = [{
        "거래일자": t.거래일자,
        "종목명":   t.종목명,
        "거래구분": t.거래구분,
        "거래수량": t.거래수량,
        "거래단가": t.거래단가,
        "거래금액": t.거래금액,
    } for t in trades]
    return _standardize(pd.DataFrame(rows))


def _extract_new_trades(baseline: pd.DataFrame, new_df: pd.DataFrame):
    """이전 데이터(baseline)에 없는 거래만 추출. 첫 업로드(baseline 비어있음)면 전체 분석.

    반환: (새 거래 df, 각 행의 new_df 내 위치 배열) — 위치는 3계층 거래별
    점수(per_trade["row"])를 앙상블 행에 매칭할 때 쓴다."""
    new_df = new_df.reset_index(drop=True)
    if baseline.empty:
        return new_df, np.arange(len(new_df))
    key = ["날짜", "종목명", "매매구분", "체결수량", "체결단가"]
    base_keys = baseline[key].drop_duplicates()
    merged = new_df.merge(base_keys, on=key, how="left", indicator=True)
    keep = merged["_merge"].to_numpy() == "left_only"
    return new_df[keep].reset_index(drop=True), np.where(keep)[0]


def _parse_user_id(raw) -> int | None:
    if raw is None:
        return None
    match = re.search(r"(\d+)$", str(raw))
    return int(match.group(1)) if match else None


def save_detection_result(user_id: str, result: dict) -> str:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = REPORTS_DIR / f"{user_id}_{timestamp}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    return str(path)


def _verdict(n_flags: int) -> str:
    return "정상" if n_flags == 0 else ("경고" if n_flags == 1 else "이상")


def _build_ensemble(
    rule_result: dict, stat_result: dict, lstm_rows: list[dict] | None = None
) -> list[dict]:
    """거래별 계층 독립 판정 + 단계형 등급.

    lstm_rows: 거래별 {score, top_bias, top_bias_명, bias_scores} 리스트 —
    rule/stat의 trade_results와 같은 순서·길이. 항목이 None이면 그 거래는
    3계층 판정 불가(시세 조회 실패·채점 실패) → flags에 deep 키 없이 두 계층만.
    """
    ensemble = []
    for i, (r, s) in enumerate(
        zip(rule_result["trade_results"], stat_result["trade_results"])
    ):
        lr = lstm_rows[i] if lstm_rows else None
        flags = {
            "rule": len(r["triggered_rules"]) > 0,
            "stat": bool(s["is_anomaly"]),
        }
        deep = None
        if lr is not None:
            flags["deep"] = lr["score"] >= DEEP_THRESHOLD
            deep = {
                "score": lr["score"],
                "top_bias": lr["top_bias"],          # "이 거래는 ~편향일 수도"
                "top_bias_명": lr.get("top_bias_명"),
                "bias_scores": lr["bias_scores"],    # 편향축별 거래 점수
                # 편향별 판정 근거(IG 분해): 이 거래 자신의 피처별 기여 상위 +
                # 현재/과거 문맥 기여율. 계산 실패 시 None
                "evidence": lr.get("evidence"),
            }
        ensemble.append({
            "날짜": r["날짜"],
            "종목명": r["종목명"],
            "verdict": _verdict(sum(flags.values())),
            "flags": flags,
            "layers_available": len(flags),
            "rule": {"score": r["rule_score"],
                     "triggered_rules": r["triggered_rules"]},
            "stat": {"score": s["stat_score"], "mahalanobis": s["mahalanobis"]},
            "deep": deep,
        })
    return ensemble


def run_pipeline_from_db(
    db: Session,
    upload_id: int,
    Trade,
    AnalysisResult,
    user_id: str = "user_001",
    job_id: int | None = None,
) -> dict:
    """
    업로드된 trades(upload_id 소속)를 DB에서 읽어 2계층 앙상블 분석.
    결과: reports/*.json 저장 + analysis_results 테이블 INSERT.

    패턴 [B]: 읽기 → commit → (트랜잭션 없이) 분석 → 쓰기 → commit.
    분석 중에는 트랜잭션을 잡지 않음.
    """
    parsed_uid = _parse_user_id(user_id)

    # ─ Phase 1: 읽기 (이번 업로드 + 이전 업로드 전체를 baseline으로)
    trades = db.query(Trade).filter(Trade.upload_id == upload_id).all()
    prev_trades = db.query(Trade).filter(Trade.upload_id < upload_id).all()
    db.commit()  # 읽기 트랜잭션 닫기 — 분석 동안 idle in transaction 회피

    base_payload = {"user_id": user_id, "upload_id": upload_id}

    if not trades:
        result = {**base_payload, "new_trades_count": 0,
                  "account_verdict": "정상",
                  "verdict_counts": {"정상": 0, "경고": 0, "이상": 0},
                  "distribution_check": {"status": "unavailable"},
                  "detection_result": {"rule": {}, "stat": {}, "ensemble": []}}
        result["saved_path"] = save_detection_result(user_id, result)
        return result

    # ─ Phase 2: 분석 (DB 안 건드림)
    std_df = _trades_to_df(trades)
    baseline = _trades_to_df(prev_trades)  # 이전 업로드들 = 비교 기준. 없으면 빈 DF → 전체 분석
    new_trades, new_pos = _extract_new_trades(baseline, std_df)

    if len(new_trades) == 0:
        result = {**base_payload, "new_trades_count": 0,
                  "account_verdict": "정상",
                  "verdict_counts": {"정상": 0, "경고": 0, "이상": 0},
                  "distribution_check": {"status": "unavailable"},
                  "detection_result": {"rule": {}, "stat": {}, "ensemble": []}}
        result["saved_path"] = save_detection_result(user_id, result)
        return result

    rule_result = run_rule_based(new_trades)
    stat_result = run_zscore(new_trades, baseline)

    # 3계층: 전체 이력(이전 + 이번 업로드) 시퀀스로 채점 후 거래별 매칭.
    # full_history 행 위치 = len(baseline) + std_df 내 위치 → per_trade["row"]와 대응.
    layer3_result = None
    lstm_rows = None
    if layer3_score is not None:
        full_history = pd.concat([baseline, std_df], ignore_index=True)
        layer3_result = layer3_score(full_history, user_id=user_id)
    if layer3_result:
        by_row = {e["row"]: e for e in layer3_result.get("per_trade", [])}
        lstm_rows = []
        for p in new_pos:
            e = by_row.get(len(baseline) + int(p))
            # 시장 맥락 없는 거래(시세 조회 실패)는 거래별 판정이 없음 —
            # 계좌 최대점수 대입은 부풀림 편향이라 그 행만 2계층 폴백(None).
            lstm_rows.append(None if e is None else {
                "score": e["trade_score"],
                "top_bias": e["top_bias"],
                "top_bias_명": e.get("top_bias_명"),
                "bias_scores": e["bias_scores"],
                "evidence": e.get("evidence"),
            })

    ensemble = _build_ensemble(rule_result, stat_result, lstm_rows)

    counts = {"정상": 0, "경고": 0, "이상": 0}
    for e in ensemble:
        counts[e["verdict"]] += 1
    # 계좌 요약(참고용) — 판정 기준은 거래별. 요약 = 거래 중 최악 등급
    account_verdict = ("이상" if counts["이상"] else
                       "경고" if counts["경고"] else "정상")

    result = {
        **base_payload,
        "new_trades_count": len(new_trades),
        "account_verdict": account_verdict,
        "verdict_counts": counts,
        # 학습 분포 대비 이탈 점검(v1 — 플래그만, 판정 불변). out_of_range면
        # 이 계좌의 딥러닝 판정은 학습 범위 밖 외삽이라 신뢰도 주의.
        "distribution_check": check_distribution(
            (layer3_result or {}).get("account_metrics")),
        "detection_result": {
            "rule": rule_result,
            "stat": stat_result,
            "layer3": layer3_result,
            "ensemble": ensemble,
        },
    }
    result["saved_path"] = save_detection_result(user_id, result)

    # ─ Phase 3: 쓰기 (새 트랜잭션)
    # xai_result가 프론트(GET /analysis/)가 받는 거래별 상세의 전부다 —
    # 조회 라우터는 저장분을 그대로 반환하므로 여기 넣지 않으면 전달되지 않는다.
    for e in ensemble:
        deep = e["deep"] or {}
        db.add(AnalysisResult(
            user_id     = parsed_uid,
            upload_id   = upload_id,
            job_id      = job_id,
            rule_score  = e["rule"]["score"],
            stat_score  = e["stat"]["score"],
            lstm_score  = deep.get("score"),  # 3계층 판정 불가 거래는 None
            final_score = None,  # 가중합 폐기 — 컬럼 정리는 스키마 작업 때
            is_anomaly  = e["verdict"] == "이상",
            xai_result  = {
                "날짜": e["날짜"],
                "종목명": e["종목명"],
                "verdict": e["verdict"],
                "flags": e["flags"],
                "layers_available": e["layers_available"],
                "triggered_rules": e["rule"]["triggered_rules"],
                "mahalanobis": e["stat"]["mahalanobis"],
                "top_bias": deep.get("top_bias"),
                "top_bias_명": deep.get("top_bias_명"),
                "bias_scores": deep.get("bias_scores"),  # 편향 4종 점수 (0~1)
                "evidence": deep.get("evidence"),        # 편향별 판정 근거(XAI)
            },
        ))
    db.commit()

    return result
