"""
detect.py
파이프라인 전체 orchestration:
CSV 읽기 → 표준화 → 새 거래 추출 → 탐지 → 결과 저장
"""

import os
import json
import pandas as pd
from datetime import datetime
from pipeline.ingest import read_csv, extract_new_trades
from pipeline.feature_eng import map_columns_with_llm, standardize, attach_market_data
from models.rule_based import run_rule_based

import logging
logging.getLogger("pykrx").setLevel(logging.ERROR)


def load_baseline_from_db(user_id: str) -> pd.DataFrame:
    """
    TODO: 실제 구현 시 AWS DB에서 user_id 기준 조회로 교체
    현재는 sample_before.csv 로컬 파일로 대체
    """
    df, cols = read_csv("data/raw/sample_before.csv")
    mapping = map_columns_with_llm(cols)
    return standardize(df, mapping)


def save_detection_result(user_id: str, result: dict) -> str:
    """
    탐지 결과를 reports/ 폴더에 JSON으로 저장
    반환: 저장된 파일 경로
    """
    os.makedirs("reports", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"reports/{user_id}_{timestamp}.json"

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    return filename


def run_pipeline(user_id: str, filepath: str) -> dict:
    """
    전체 파이프라인 실행
    반환: {
        "user_id": str,
        "new_trades_count": int,
        "detection_result": dict,
        "saved_path": str
    }
    """
    # 1. CSV 읽기
    df, cols = read_csv(filepath)

    # 2. LLM 컬럼 매핑
    mapping = map_columns_with_llm(cols)

    # 3. 표준 포맷 변환
    std_df = standardize(df, mapping)

    # 4. 시장 데이터 병합
    std_df = attach_market_data(std_df)

    # 5. DB에서 기존 기준선 로드
    baseline = load_baseline_from_db(user_id)

    # 6. 날짜 기준 새 거래 추출
    new_trades = extract_new_trades(baseline, std_df)

    # 7. Rule-based 탐지
    detection_result = run_rule_based(new_trades)

    # 8. 결과 저장
    result = {
        "user_id": user_id,
        "new_trades_count": len(new_trades),
        "detection_result": detection_result
    }
    saved_path = save_detection_result(user_id, result)
    result["saved_path"] = saved_path

    return result

if __name__ == "__main__":
    result = run_pipeline(
        user_id="user_001",
        filepath="data/raw/sample_after.csv"
    )
    print(result)