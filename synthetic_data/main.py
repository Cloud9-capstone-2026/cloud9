"""
Canary Base Agent 합성 데이터 생성기 - 엔트리포인트

실행: python -m synthetic_data.main  (레포 최상위에서)
이 파일 하나만 실행하면 synthetic_data/ 패키지 전체(가격 데이터 로드 -> agent 시뮬레이션
-> 3파일 패키징)가 한 번에 돈다. 다중 시드·모드 데이터셋은 generate_dataset.py 사용.

출력 3파일 (7-4 패키징 — 라벨/메타 분리로 leakage 물리 차단):
- trades : 거래 로그, 실계좌 스키마와 동일한 11필드
           (schema.Trade 13필드에서 처리시간·편향라벨 제거 — 처리시간은 uniform
           아티팩트 블랙리스트, 편향라벨은 학습 타깃. 학습 입력 = 추론 입력 모양)
- labels : agent_id + 4개 편향 파라미터(학습 타깃) + 생성모드(파일 단위 상수 —
           agent 간 무변동이라 누설 불가. 측정 통계량은 features로 재계산 가능한
           파생값이라 미포함 — 단일 진실 원천)
- meta   : 그룹 태그(표 Ⅲ-1 4축)·진입일·초기 보유 정보 + 확장 샘플링 성분 4컬럼
           (7-5) — 분석 전용, ML 학습 사용 금지. 성분 플래그는 agent별 가변
           비타깃 정보라 labels가 아닌 여기에 둔다(leakage 원칙)
- trade_labels : 거래별 인과 귀속 확률 4종 (2단계) — trades와 행 순서 1:1.
           "이 거래가 각 편향 채널 때문에 발생했을 확률"(반사실 비·성분 비중,
           schema.Trade.귀속라벨 주석 참조). 시퀀스 태깅 모델의 학습 타깃 전용
"""

import pandas as pd

from . import config
from .model import MarketModel

# 실계좌 11필드 스키마 (features.load_trades_csv의 기대 입력과 동일)
TRADES_COLUMNS = [
    "거래일자", "agent_id", "종목코드", "거래구분", "거래수량", "거래단가",
    "거래금액", "수수료", "거래세", "정산금액", "예수금",
]
_BIAS_PARAMS = list(config.NEUTRAL_VALUES)  # 4개 편향 파라미터 명


def package_outputs(model, trades_path, labels_path, meta_path,
                    trade_labels_path=None, quiet=False):
    """run() 끝난 model을 trades/labels/meta(+trade_labels) 파일로 기록.
    반환: (거래수, agent수)."""
    df = model.trades_to_dataframe()[TRADES_COLUMNS]
    df.to_csv(trades_path, index=False, encoding="utf-8-sig")

    if trade_labels_path:  # 거래별 인과 귀속 (행 순서 = trades와 1:1)
        tl = pd.DataFrame(
            {
                "agent_id": t.agent_id,
                "거래일자": t.거래일자,
                "거래구분": t.거래구분,
                "attr_disposition": t.귀속라벨.get("disposition", 0.0),
                "attr_overconfidence": t.귀속라벨.get("overconfidence", 0.0),
                "attr_lottery": t.귀속라벨.get("lottery", 0.0),
                "attr_herd": t.귀속라벨.get("herd", 0.0),
            }
            for t in model.trades
        )
        tl.to_csv(trade_labels_path, index=False, encoding="utf-8-sig")

    labels = pd.DataFrame(
        {
            "agent_id": str(a.unique_id),
            **{p: getattr(a.params, p) for p in _BIAS_PARAMS},
            "생성모드": model.mode,
        }
        for a in model.agents
    )
    labels.to_csv(labels_path, index=False, encoding="utf-8-sig")

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
            **{
                f"모드_{p}": model.param_components.get(str(a.unique_id), {}).get(p, "natural")
                for p in _BIAS_PARAMS
            },
        }
        for a in model.agents
    )
    meta.to_csv(meta_path, index=False, encoding="utf-8-sig")

    if not quiet:
        print(f"거래 {len(df):,}건 → {trades_path} ({len(df.columns)}필드)")
        print(f"라벨 {len(labels):,}건 → {labels_path}")
        print(f"메타 {len(meta):,}건 → {meta_path} (학습 비사용 — 분석 전용)")
    return len(df), len(labels)


def main():
    model = MarketModel(
        n_investors=config.N_INVESTORS,
        tickers=config.UNIVERSE_TICKERS,
        seed=config.RANDOM_SEED,
    )
    model.run()
    package_outputs(
        model, config.OUTPUT_CSV_PATH, config.LABELS_CSV_PATH, config.META_CSV_PATH,
        trade_labels_path=config.TRADE_LABELS_CSV_PATH,
    )


if __name__ == "__main__":
    main()
