"""
KCMI 재현 밴드 검증 (느린 층) — 실행: pytest -m slow

자연 모드 시뮬레이션을 시드 3개(7 + 평가 시드)로 돌려, 합성 데이터가 실제
한국 투자자 통계(KCMI 22-02)를 ±10% 밴드 안에서 재현하는지 3시드 평균으로
판정한다. 생성기·설정을 고칠 때 "현실 재현이 깨지지 않았나"의 자동 관문 —
기존에 수동으로 하던 판정을 테스트로 옮긴 것 (판정 기준 동일).

전제: 시세 캐시(synthetic_data/.cache) 존재 — 없으면 skip (테스트는 네트워크
호출을 하지 않는다는 원칙 유지). 고정 시드 + 고정 캐시라 결과는 결정론적.
실행 시간 약 2분.
"""

import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.slow

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from synthetic_data import config  # noqa: E402

_has_cache = any(Path(config.PRICE_CACHE_DIR).glob("ohlcv_v2*.parquet")) \
    if Path(config.PRICE_CACHE_DIR).exists() else False
if not _has_cache:
    pytest.skip("시세 캐시 없음 — 네트워크 없이 시뮬 불가", allow_module_level=True)

SEEDS = [7, *config.DATASET_EVAL_SEEDS]
BAND = 0.10  # 목표 ±10%

# 목표치: synthetic_data.validation.kcmi_metrics.KCMI_TARGETS + 복권 H-L 앵커
# (KCMI 22-02 Ⅳ-13, 거래 H-L ~ +51%p — kcmi_metrics 리포트 주석 참조)
TARGETS = {"disposition": 2.18, "turnover": 7.14, "holding_mean": 9.67,
           "lottery_hml": 0.51}
HOLDING_MEDIAN = 3.0  # 중앙값은 이산값이라 밴드가 아닌 일치로 판정


@pytest.fixture(scope="module")
def seed_metrics():
    """시드별 자연 모드 시뮬 1회씩 → 핵심 지표 dict 목록."""
    from synthetic_data.core.model import MarketModel
    from synthetic_data.validation.kcmi_metrics import compute_metrics

    out = []
    for seed in SEEDS:
        model = MarketModel(n_investors=config.N_INVESTORS,
                            tickers=config.UNIVERSE_TICKERS,
                            seed=seed, mode="natural")
        model.run()
        r = compute_metrics(model)
        out.append({
            "seed": seed,
            "disposition": r["disposition"]["ratio"],
            "turnover": r["turnover"]["annual"],
            "holding_mean": r["holding"]["mean"],
            "holding_median": r["holding"]["median"],
            "lottery_hml": r["lottery"]["trading"]["HmL"],
        })
    return out


def _mean(seed_metrics, key):
    return sum(m[key] for m in seed_metrics) / len(seed_metrics)


@pytest.mark.parametrize("key", sorted(TARGETS))
def test_metric_within_band(seed_metrics, key):
    got = _mean(seed_metrics, key)
    target = TARGETS[key]
    lo, hi = target * (1 - BAND), target * (1 + BAND)
    detail = ", ".join(f"s{m['seed']}={m[key]:.3f}" for m in seed_metrics)
    assert lo <= got <= hi, (
        f"{key}: 3시드 평균 {got:.3f}이 밴드 [{lo:.3f}, {hi:.3f}] 밖 "
        f"(목표 {target}, {detail})")


def test_holding_median_exact(seed_metrics):
    for m in seed_metrics:
        assert m["holding_median"] == HOLDING_MEDIAN, (
            f"s{m['seed']}: 보유 중앙값 {m['holding_median']} != {HOLDING_MEDIAN}")
