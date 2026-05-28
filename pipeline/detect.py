"""
detect.py
Rule-based → Z-score(+마할라노비스) 2계층 탐지 후 서버로 결과 전송
"""

import os
import json
import httpx
import pandas as pd
from datetime import datetime
from pipeline.ingest import read_csv, extract_new_trades
from pipeline.feature_eng import map_columns_with_llm, standardize, attach_market_data
from models.rule_based import run_rule_based
from models.zscore import run_zscore

import logging
logging.getLogger("pykrx").setLevel(logging.ERROR)

BACKEND_URL = "http://localhost:8000/analysis/"


def load_baseline_from_db(user_id: str) -> pd.DataFrame:
    df, cols = read_csv("backend/persona_a_clean.csv")
    mapping = map_columns_with_llm(cols)
    return standardize(df, mapping)


def save_detection_result(user_id: str, result: dict) -> str:
    os.makedirs("reports", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"reports/{user_id}_{timestamp}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    return filename


def send_to_server(result: dict):
    try:
        response = httpx.post(BACKEND_URL, json=result, timeout=5)
        response.raise_for_status()
        print(f"[서버 전송 완료] {result['user_id']} {response.json()}")
    except Exception as ex:
        print(f"[서버 전송 실패] {result['user_id']} {ex}")


def run_pipeline(user_id: str, filepath: str) -> dict:
    # 1. CSV 읽기
    df, cols = read_csv(filepath)

    # 2. LLM 컬럼 매핑
    mapping = map_columns_with_llm(cols)

    # 3. 표준화
    std_df = standardize(df, mapping)

    # 4. 시장 데이터 병합
    std_df = attach_market_data(std_df)
    print("attach 후:", len(std_df))

    # 5. 기준선 로드
    baseline = load_baseline_from_db(user_id)
    print("baseline 마지막 날짜:", baseline["날짜"].max())

    # 6. 새 거래 추출
    new_trades = extract_new_trades(baseline, std_df)
    print("new_trades:", len(new_trades))
    print(new_trades)

    # 7. 1계층: Rule-based (거래별)
    rule_result = run_rule_based(new_trades)

    # 8. 2계층: Z-score + 마할라노비스 (거래별)
    stat_result = run_zscore(new_trades, baseline)

    # 9. 앙상블: 거래별 final_score = 0.3*rule + 0.7*stat
    RULE_W, STAT_W = 0.3, 0.7
    FINAL_THRESHOLD = 0.5

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
            "mahalanobis": s["mahalanobis"]
        })

    result = {
        "user_id": user_id,
        "new_trades_count": len(new_trades),
        "detection_result": {
            "rule": rule_result,
            "stat": stat_result,
            "ensemble": ensemble
        }
    }

    # 10. 로컬 저장
    saved_path = save_detection_result(user_id, result)

    # 11. 서버 전송 (저장된 JSON 파일과 동일한 페이로드)
    send_to_server(result)

    result["saved_path"] = saved_path
    return result


if __name__ == "__main__":
    result = run_pipeline(
        user_id="user_001",
        filepath="backend/persona_a_trades.csv"
    )
    print(result)