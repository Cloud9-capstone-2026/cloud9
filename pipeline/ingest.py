"""
ingest.py
CSV 읽기 + 2행 병합 + 새 거래 추출
"""

import pandas as pd


def read_csv(filepath: str) -> tuple[pd.DataFrame, list[str]]:
    """
    CSV 파일을 읽고 키움처럼 2행 구조인 경우 1행으로 병합.
    반환: (DataFrame, 원본 컬럼 목록)
    """
    raw = pd.read_csv(filepath, header=None)

    if _is_two_row_header(raw):
        header_row1 = raw.iloc[0].fillna("").astype(str).tolist()
        header_row2 = raw.iloc[1].fillna("").astype(str).tolist()
        data_rows = raw.iloc[2:].reset_index(drop=True)
        df = _merge_two_row_data(data_rows, header_row1, header_row2)
    else:
        df = pd.read_csv(filepath)

    return df, df.columns.tolist()


def _is_two_row_header(raw: pd.DataFrame) -> bool:
    try:
        pd.to_datetime(str(raw.iloc[2, 0]))
        return True
    except Exception:
        return False


def _merge_two_row_data(data: pd.DataFrame, h1: list, h2: list) -> pd.DataFrame:
    """홀수행 + 짝수행 → 하나의 거래 행으로 병합"""
    records = []
    for i in range(0, len(data) - 1, 2):
        row1 = data.iloc[i]
        row2 = data.iloc[i + 1]
        record = {}
        for j, col in enumerate(h1):
            if col:
                record[col] = row1.iloc[j]
        for j, col in enumerate(h2):
            if col:
                record[col] = row2.iloc[j]
        records.append(record)
    return pd.DataFrame(records)


def extract_new_trades(baseline_df: pd.DataFrame, new_df: pd.DataFrame) -> pd.DataFrame:
    """날짜 기준: 기존 마지막 날짜 이후 거래만 추출"""
    last_date = baseline_df["날짜"].max()
    new_trades = new_df[new_df["날짜"] > last_date].copy()
    return new_trades.reset_index(drop=True)