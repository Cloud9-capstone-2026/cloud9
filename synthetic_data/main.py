"""
Canary Base Agent 합성 데이터 생성기 - 엔트리포인트

실행: python -m synthetic_data.main  (레포 최상위에서)
이 파일 하나만 실행하면 synthetic_data/ 패키지 전체(가격 데이터 로드 -> agent 시뮬레이션
-> 3파일 패키징)가 한 번에 돈다.

출력 3파일 (7-4 패키징 — 라벨/메타 분리로 leakage 물리 차단):
- synthetic_trades.csv : 거래 로그, 실계좌 스키마와 동일한 11필드
                         (schema.Trade 13필드에서 처리시간·편향라벨 제거 —
                         처리시간은 uniform 아티팩트 블랙리스트, 편향라벨은 학습 타깃.
                         학습 입력이 추론 입력과 같은 모양이 되는 것이 목적)
- synthetic_labels.csv : agent_id + 4개 편향 파라미터(학습 타깃) + 생성 모드 플래그
                         ("natural" — 7-5 확장 분포 모드 대비. 측정 통계량은 여기 안
                         넣는다: features.build_features로 언제든 재계산 가능한 파생값
                         이라 단일 진실 원천 유지)
- synthetic_meta.csv   : 그룹 태그(표 Ⅲ-1 4축)·진입일·초기 보유 정보 — 분석 전용,
                         ML 학습에 사용 금지(실계좌에 없는 정보)
"""

import pandas as pd

from . import config
from .model import MarketModel

# 실계좌 11필드 스키마 (features.load_trades_csv의 기대 입력과 동일)
TRADES_COLUMNS = [
    "거래일자", "agent_id", "종목코드", "거래구분", "거래수량", "거래단가",
    "거래금액", "수수료", "거래세", "정산금액", "예수금",
]


def main():
    model = MarketModel(
        n_investors=config.N_INVESTORS,
        tickers=config.UNIVERSE_TICKERS,
        seed=config.RANDOM_SEED,
    )
    model.run()

    # --- trades (11필드) ---
    df = model.trades_to_dataframe()[TRADES_COLUMNS]
    df.to_csv(config.OUTPUT_CSV_PATH, index=False, encoding="utf-8-sig")
    print(f"거래 {len(df):,}건 → {config.OUTPUT_CSV_PATH} ({len(df.columns)}필드)")

    # --- labels (학습 타깃) ---
    labels = pd.DataFrame(
        {
            "agent_id": str(a.unique_id),
            "disposition_strength": a.params.disposition_strength,
            "overconfidence": a.params.overconfidence,
            "lottery_preference": a.params.lottery_preference,
            "herd_sensitivity": a.params.herd_sensitivity,
            "생성모드": "natural",
        }
        for a in model.agents
    )
    labels.to_csv(config.LABELS_CSV_PATH, index=False, encoding="utf-8-sig")
    print(f"라벨 {len(labels):,}건 → {config.LABELS_CSV_PATH}")

    # --- meta (분석 전용 — 학습 비사용) ---
    meta = pd.DataFrame(
        {
            "agent_id": str(a.unique_id),
            "신규여부": a.group.new_key,
            "성별": a.group.gender,
            "연령": a.group.age,
            "자산": a.group.asset,
            "진입일": a.entry_date,
            "초기보유종목수": len(model.initial_positions.get(str(a.unique_id), {})),
            "초기총자산": model.initial_assets.get(str(a.unique_id)),
        }
        for a in model.agents
    )
    meta.to_csv(config.META_CSV_PATH, index=False, encoding="utf-8-sig")
    print(f"메타 {len(meta):,}건 → {config.META_CSV_PATH} (학습 비사용 — 분석 전용)")

    if not df.empty:
        print("\n매수/매도 비율:")
        print(df["거래구분"].value_counts(normalize=True))


if __name__ == "__main__":
    main()
