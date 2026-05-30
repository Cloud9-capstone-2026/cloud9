"""
detect.py
DB(trades) 기반 2계층 앙상블 탐지 — Rule-based + Z-score(+마할라노비스)
업로드 직후 in-process로 호출되어 reports/*.json 저장 + AnalysisResult INSERT.
"""

import json
import re
import logging
from pathlib import Path
from datetime import datetime

import pandas as pd
from sqlalchemy.orm import Session

from models.rule_based import run_rule_based
from models.zscore import run_zscore

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

BASELINE_PATH = BACKEND_DIR / "persona_a_clean.csv"
REPORTS_DIR = BACKEND_DIR / "reports"

RULE_W, STAT_W = 0.3, 0.7
FINAL_THRESHOLD = 0.5


def _standardize(df: pd.DataFrame) -> pd.DataFrame:
    """DB/CSV 컬럼명을 모델 표준 컬럼명으로 변환 + 타입 정리."""
    df = df.rename(columns=DB_TO_STANDARD)
    df["날짜"] = pd.to_datetime(df["날짜"])
    for col in ["체결수량", "체결단가", "총거래금액"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.sort_values("날짜").reset_index(drop=True)


def _trades_to_df(trades: list) -> pd.DataFrame:
    """Trade ORM 객체 리스트 → 표준 DataFrame."""
    rows = [{
        "거래일자": t.거래일자,
        "종목명":   t.종목명,
        "거래구분": t.거래구분,
        "거래수량": t.거래수량,
        "거래단가": t.거래단가,
        "거래금액": t.거래금액,
    } for t in trades]
    return _standardize(pd.DataFrame(rows))


def _load_baseline() -> pd.DataFrame:
    df = pd.read_csv(BASELINE_PATH)
    return _standardize(df)


def _extract_new_trades(baseline: pd.DataFrame, new_df: pd.DataFrame) -> pd.DataFrame:
    last_date = baseline["날짜"].max()
    return new_df[new_df["날짜"] > last_date].copy().reset_index(drop=True)


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


def _build_ensemble(rule_result: dict, stat_result: dict) -> list[dict]:
    ensemble = []
    for r, s in zip(rule_result["trade_results"], stat_result["trade_results"]):
        final_score = RULE_W * r["rule_score"] + STAT_W * s["stat_score"]
        ensemble.append({
            "날짜": r["날짜"],
            "종목명": r["종목명"],
            "rule_score": r["rule_score"],
            "stat_score": s["stat_score"],
            "final_score": round(final_score, 4),
            "is_anomaly": final_score > FINAL_THRESHOLD,
            "triggered_rules": r["triggered_rules"],
            "mahalanobis": s["mahalanobis"],
        })
    return ensemble


def run_pipeline_from_db(
    db: Session,
    upload_id: int,
    Trade,
    AnalysisResult,
    user_id: str = "user_001",
) -> dict:
    """
    업로드된 trades(upload_id 소속)를 DB에서 읽어 2계층 앙상블 분석.
    결과: reports/*.json 저장 + analysis_results 테이블 INSERT.

    패턴 [B]: 읽기 → commit → (트랜잭션 없이) 분석 → 쓰기 → commit.
    분석 중에는 트랜잭션을 잡지 않음.
    """
    parsed_uid = _parse_user_id(user_id)

    # ─ Phase 1: 읽기
    trades = db.query(Trade).filter(Trade.upload_id == upload_id).all()
    db.commit()  # 읽기 트랜잭션 닫기 — 분석 동안 idle in transaction 회피

    base_payload = {"user_id": user_id, "upload_id": upload_id}

    if not trades:
        result = {**base_payload, "new_trades_count": 0,
                  "detection_result": {"rule": {}, "stat": {}, "ensemble": []}}
        result["saved_path"] = save_detection_result(user_id, result)
        return result

    # ─ Phase 2: 분석 (DB 안 건드림)
    std_df = _trades_to_df(trades)
    baseline = _load_baseline()
    new_trades = _extract_new_trades(baseline, std_df)

    if len(new_trades) == 0:
        result = {**base_payload, "new_trades_count": 0,
                  "detection_result": {"rule": {}, "stat": {}, "ensemble": []}}
        result["saved_path"] = save_detection_result(user_id, result)
        return result

    rule_result = run_rule_based(new_trades)
    stat_result = run_zscore(new_trades, baseline)
    ensemble = _build_ensemble(rule_result, stat_result)

    result = {
        **base_payload,
        "new_trades_count": len(new_trades),
        "detection_result": {
            "rule": rule_result,
            "stat": stat_result,
            "ensemble": ensemble,
        },
    }
    result["saved_path"] = save_detection_result(user_id, result)

    # ─ Phase 3: 쓰기 (새 트랜잭션)
    for e in ensemble:
        db.add(AnalysisResult(
            user_id     = parsed_uid,
            upload_id   = upload_id,
            rule_score  = e["rule_score"],
            stat_score  = e["stat_score"],
            lstm_score  = None,
            final_score = e["final_score"],
            is_anomaly  = e["is_anomaly"],
            xai_result  = {
                "날짜": e["날짜"],
                "종목명": e["종목명"],
                "triggered_rules": e["triggered_rules"],
                "mahalanobis": e["mahalanobis"],
            },
        ))
    db.commit()

    return result
