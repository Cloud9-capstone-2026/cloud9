"""
골든 상수 1회 산출 — test_feature_golden.py의 동결 값 갱신용.

실행: 레포 루트에서  python backend/tests/capture_golden.py
픽스처와 동일한 데이터를 conftest의 make_* 함수로 재생성하므로
테스트가 보는 값과 정의상 같다. 출력값을 test_feature_golden.py 하단
상수에 붙여넣고, 갱신 사유를 커밋 메시지에 남길 것.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from conftest import make_index_df, make_price_df, make_synthetic_trades  # noqa: E402


def main():
    from synthetic_data.features import build_features

    price_df = make_price_df()
    index_df = make_index_df(price_df)
    trades = make_synthetic_trades(price_df)
    out = build_features(trades.copy(), price_df, index_df, windows=(None,))
    ev = out["events"].reset_index(drop=True)

    for i, col in [(0, "prior_ret1"), (4, "abn_vol"), (5, "abn_vol")]:
        print(f"({i}, {col!r}): {float(ev.loc[i, col])!r}")


if __name__ == "__main__":
    main()
