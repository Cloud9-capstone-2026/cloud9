"""
3계층 학습 데이터 준비 (최소 슬라이스 1단계).

실행: python -m ml.train.prepare  (레포 최상위에서, dataset/ 생성 이후)
산출: ml/cache/{세트명}_events.parquet, {세트명}_aggregates.parquet

dataset/ 7세트(학습 확장 5 + 평가 자연 2)의 trades CSV를 synthetic_data.features의
빌더에 통과시켜 캐싱한다 — 학습 스크립트(train_tagger)가 매 실험마다 build_features를
재계산하지 않게 하기 위한 것. 시세·지수는 synthetic_data/.cache의 로컬 parquet을
그대로 쓰므로 네트워크가 필요 없다.

aggregates는 GBDT 베이스라인용으로 full 창만 계산한다(63d/21d는 이 슬라이스 미사용).
산출물은 재생성 가능한 파생 데이터 — .gitignore 대상.
"""

import os
import sys

import pandas as pd

from synthetic_data import config
from synthetic_data.features import build_features, load_trades_csv
from synthetic_data.market.lott import load_lott_table
from synthetic_data.market_data import get_index_data, get_price_data

CACHE_DIR = os.path.join("ml", "cache")


def dataset_names() -> list[str]:
    manifest = pd.read_csv(os.path.join(config.DATASET_DIR, "manifest.csv"))
    return list(manifest["name"])


def prepare_one(name: str, price_df, index_df, force: bool = False):
    ev_path = os.path.join(CACHE_DIR, f"{name}_events.parquet")
    ag_path = os.path.join(CACHE_DIR, f"{name}_aggregates.parquet")
    if not force and os.path.exists(ev_path) and os.path.exists(ag_path):
        print(f"{name}: 캐시 존재 — 스킵", flush=True)
        return
    trades, _ = load_trades_csv(config.dataset_path(name, "trades"))
    out = build_features(trades, price_df, index_df, windows=(None,),
                         lott_table=load_lott_table(config.LOTT_TABLE_PATH))  # 생성기·추론과 같은 표
    ev = out["events"].copy()
    ev["거래일자"] = pd.to_datetime(ev["거래일자"])  # date → datetime64 (parquet 호환)
    ev.to_parquet(ev_path, index=False)
    out["aggregates"].to_parquet(ag_path, index=False)
    print(f"{name}: events {len(ev):,}행, aggregates {len(out['aggregates']):,}행",
          flush=True)


def main():
    os.makedirs(CACHE_DIR, exist_ok=True)
    print("시세·지수 로드 (로컬 캐시)...", flush=True)
    price_df = get_price_data(config.UNIVERSE_TICKERS)
    index_df = get_index_data()
    force = "--force" in sys.argv
    for name in dataset_names():
        prepare_one(name, price_df, index_df, force=force)
    print("완료.", flush=True)


if __name__ == "__main__":
    main()
