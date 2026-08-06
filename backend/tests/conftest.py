"""
분석 파이프라인 회귀 테스트 공용 픽스처 (리팩터 안전망).

원칙:
- 라이브 pykrx 호출 금지 — 시세·지수·종목명 매핑 전부 코드 생성 픽스처로 주입
- 실제 모델 아티팩트(tagger.pt)·Release 다운로드 비의존 — layer3 계약 테스트는
  고정 시드 가짜 태거(fake_layer3)를 주입해 돌린다. 검증 대상이 입력→피처→
  행 매칭→반환 구조의 배관 계약이지 모델 성능이 아니기 때문.
- 값은 전부 결정론적(수식 + 고정 시드)이라 골든 스냅샷이 성립

픽스처 데이터는 모듈 함수(make_*)로 분리 — capture_golden.py가 pytest 없이
같은 데이터를 재생성해 골든 상수를 산출한다.

실행: 레포 루트에서  python -m pytest backend/tests -q
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

_REPO = Path(__file__).resolve().parents[2]
for p in (str(_REPO), str(_REPO / "backend")):
    if p not in sys.path:
        sys.path.insert(0, p)

TICKERS = ["000010", "000020", "000030"]
NAMES = {"000010": "테스트A", "000020": "테스트B", "000030": "테스트C"}


def make_price_df() -> pd.DataFrame:
    """가짜 OHLCV — market_data 스키마(종목코드·거래일자·시가·고가·저가·종가·거래량).

    90거래일, 종목별 추세+진동 수식. 70~74일은 거래량 급증(abn_vol 신호용).
    """
    days = pd.bdate_range("2020-03-02", periods=90).date
    rng = np.random.default_rng(0)
    frames = []
    for k, tk in enumerate(TICKERS):
        t = np.arange(len(days))
        close = 10_000 * (k + 1) * (1 + 0.001 * t + 0.03 * np.sin(t / 7))
        close = np.round(close)
        spread = np.maximum(1, np.round(close * 0.02))
        vol = np.full(len(days), 50_000.0) + rng.integers(0, 1_000, len(days))
        vol[70:75] *= 5  # 거래량 급증 구간
        frames.append(pd.DataFrame({
            "종목코드": tk,
            "거래일자": days,
            "시가": close - spread // 2,
            "고가": close + spread,
            "저가": close - spread,
            "종가": close,
            "거래량": vol,
        }))
    return pd.concat(frames, ignore_index=True)


def make_index_df(price_df: pd.DataFrame) -> pd.DataFrame:
    days = sorted(price_df["거래일자"].unique())
    t = np.arange(len(days))
    return pd.DataFrame({"거래일자": days,
                         "종가": 200.0 + 0.5 * t + 3 * np.sin(t / 5)})


def _close(price_df, tk, day):
    sel = price_df[(price_df["종목코드"] == tk) & (price_df["거래일자"] == day)]
    return float(sel["종가"].iloc[0])


def make_synthetic_trades(price_df: pd.DataFrame) -> pd.DataFrame:
    """합성 스키마 거래 8건 (단일 계좌) — 이익 매도·손실 매도·재매수 포함.

    체결가는 픽스처 종가 그대로 → return_at_sale을 손으로 검산 가능.
    """
    days = sorted(price_df["거래일자"].unique())
    rows = []

    def add(day_i, tk, side, qty, price=None):
        p = price if price is not None else _close(price_df, tk, days[day_i])
        rows.append({
            "거래일자": days[day_i], "agent_id": "u1", "종목코드": tk,
            "거래구분": side, "거래수량": qty, "거래단가": p,
            "거래금액": qty * p, "수수료": 0, "거래세": 0,
            "정산금액": qty * p, "예수금": 0,
        })

    add(60, "000010", "매수", 10)
    add(63, "000020", "매수", 5)
    add(66, "000010", "매도", 10)          # 60일 종가 대비 손익 = 66일/60일 종가비
    add(68, "000030", "매수", 20)
    add(71, "000020", "매도", 5)           # 급증 구간 안 — abn_vol 유효
    add(74, "000010", "매수", 8)
    add(80, "000030", "매도", 20)
    add(85, "000010", "매도", 8)
    return pd.DataFrame(rows)


@pytest.fixture(scope="session")
def price_df() -> pd.DataFrame:
    return make_price_df()


@pytest.fixture(scope="session")
def index_df(price_df) -> pd.DataFrame:
    return make_index_df(price_df)


@pytest.fixture(scope="session")
def synthetic_trades(price_df) -> pd.DataFrame:
    return make_synthetic_trades(price_df)


@pytest.fixture(scope="session")
def standard_trades(synthetic_trades) -> pd.DataFrame:
    """백엔드 표준 컬럼(날짜·종목명·매매구분·체결수량·체결단가·총거래금액) 버전."""
    df = synthetic_trades
    return pd.DataFrame({
        "날짜": pd.to_datetime(df["거래일자"]),
        "종목명": df["종목코드"].map(NAMES),
        "매매구분": df["거래구분"],
        "체결수량": df["거래수량"],
        "체결단가": df["거래단가"],
        "총거래금액": df["거래금액"],
    })


@pytest.fixture()
def no_network_layer3(monkeypatch, price_df, index_df):
    """layer3의 시세·지수 조회와 종목명 매핑을 픽스처로 대체 (네트워크 0)."""
    from models import layer3

    monkeypatch.setattr(layer3, "_fetch_price_df",
                        lambda tickers, d_min, d_max: price_df)
    monkeypatch.setattr(layer3, "_fetch_index_df", lambda pdf: index_df)

    from pipeline import feature_eng
    code_of = {v: k for k, v in NAMES.items()}
    monkeypatch.setattr(feature_eng, "get_ticker_code",
                        lambda name: code_of.get(name))
    return layer3


@pytest.fixture()
def fake_layer3(monkeypatch):
    """layer3._load_artifacts를 가짜 태거로 대체 — 실제 tagger.pt·Release 비의존.

    고정 시드로 초기화한 소형 GRUTagger(학습 안 됨)라 점수 값은 무의미하지만
    결정론적이므로 반환 구조·값 범위·행 1:1 매칭·재현성 계약 검증에는 충분하다.
    norm_stats는 항등(mean 0, std 1) — 배관 검증에 통계 값은 무관.
    """
    torch = pytest.importorskip("torch")
    from models import layer3
    from ml import seqfeat
    from ml.gru_model import GRUTagger

    attrs = ["attr_disposition", "attr_overconfidence", "attr_lottery", "attr_herd"]
    meta = {
        "attrs": attrs,
        "attr_param": {
            "attr_disposition": "disposition_strength",
            "attr_overconfidence": "overconfidence",
            "attr_lottery": "lottery_preference",
            "attr_herd": "herd_sensitivity",
        },
        "norm_stats": {f: {"mean": 0.0, "std": 1.0} for f in seqfeat.NORM_FEATURES},
        "max_len": 64,
        "model": {"n_channels": seqfeat.N_CHANNELS, "hidden": 8, "layers": 1,
                  "dropout": 0.0},
    }
    torch.manual_seed(0)
    model = GRUTagger(seqfeat.N_CHANNELS, 8, 1, len(attrs))
    model.eval()
    monkeypatch.setattr(layer3, "_load_artifacts", lambda: (model, meta))
    return layer3
