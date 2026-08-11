"""
layer3 입출력 계약 테스트 — 시세 캐시 교체 등 배관 변경 중에도
반환 구조·값 범위·행 매칭이 변하지 않음을 보증한다.

기본은 가짜 태거(conftest.fake_layer3) 주입 — 실제 모델·Release·pykrx 비의존.
검증 대상이 입력→피처→행 매칭→반환 구조의 배관 계약이지 모델 성능이 아니라서다.
실제 아티팩트 통합 테스트는 마지막 1개만 (로컬에 tagger.pt 있을 때만보너스로 실행).
"""

import pytest

pytest.importorskip("torch", reason="torch 미설치 환경 — layer3 자체가 비활성")

from pathlib import Path

_ART = Path(__file__).resolve().parents[2] / "ml" / "artifacts"
needs_artifacts = pytest.mark.skipif(
    not (_ART / "tagger.pt").exists(),
    reason="모델 아티팩트 없음 (로컬 학습 산출 또는 Release 필요)",
)

BIAS_PARAMS = {"disposition_strength", "overconfidence",
               "lottery_preference", "herd_sensitivity"}


def _assert_contract(out, n_trades):
    """score_* 공통 계약: 구조·값 범위·행 1:1 매칭·요약 규약."""
    assert out is not None, "픽스처 입력에서 채점 실패하면 안 됨 (경고 로그 확인)"
    assert set(out) >= {"per_trade", "lstm_score", "bias_mean", "n_events"}
    assert out["n_events"] == n_trades  # max_len 안 — 전 거래 채점
    assert 0.0 <= out["lstm_score"] <= 1.0

    rows_seen = set()
    for e in out["per_trade"]:
        assert set(e) >= {"row", "거래일자", "종목코드", "거래구분",
                          "bias_scores", "top_bias", "top_bias_명", "trade_score"}
        assert set(e["bias_scores"]) == BIAS_PARAMS
        assert all(0.0 <= v <= 1.0 for v in e["bias_scores"].values())
        assert e["trade_score"] == max(e["bias_scores"].values())
        assert e["top_bias"] in BIAS_PARAMS
        rows_seen.add(e["row"])
    assert rows_seen == set(range(n_trades))  # 행 매칭 1:1

    # lstm_score = 거래 점수의 최댓값 (문서화된 요약 규약)
    assert out["lstm_score"] == max(e["trade_score"] for e in out["per_trade"])


def test_score_from_trades_contract(fake_layer3, synthetic_trades, price_df, index_df):
    out = fake_layer3.score_from_trades(
        synthetic_trades, price_df=price_df, index_df=index_df
    )
    _assert_contract(out, len(synthetic_trades))


def test_score_account_contract(fake_layer3, no_network_layer3, standard_trades):
    """표준 컬럼 입력 → 종목명 매핑 → 합성 스키마 변환 경로까지 포함한 계약.

    per_trade["row"]는 표준 입력의 행 위치 — detect.py 매칭 규약.
    """
    out = fake_layer3.score_account(standard_trades, user_id="tester")
    _assert_contract(out, len(standard_trades))


def test_account_metrics_for_distribution_check(fake_layer3, synthetic_trades,
                                                price_df, index_df):
    """분포 점검(v1) 재료 — 계좌 지표 6종이 기준 분포와 같은 키로 산출된다."""
    out = fake_layer3.score_from_trades(
        synthetic_trades, price_df=price_df, index_df=index_df
    )
    m = out["account_metrics"]
    assert set(m) == {"turnover_annual", "buy_share", "mean_abn_vol_at_buy",
                      "mean_lott_at_buy", "holding_days_mean", "n_trades"}
    assert m["n_trades"] == len(synthetic_trades)
    assert 0.0 <= m["buy_share"] <= 1.0
    assert m["holding_days_mean"] is None or m["holding_days_mean"] > 0


def test_score_from_trades_deterministic(fake_layer3, synthetic_trades,
                                         price_df, index_df):
    """같은 입력 → 같은 출력 (캐시 도입 후에도 유지돼야 하는 성질)."""
    a = fake_layer3.score_from_trades(
        synthetic_trades, price_df=price_df, index_df=index_df
    )
    b = fake_layer3.score_from_trades(
        synthetic_trades, price_df=price_df, index_df=index_df
    )
    assert a == b


@needs_artifacts
def test_real_artifacts_integration(synthetic_trades, price_df, index_df):
    """실제 tagger.pt 로드 경로 통합 확인 (로컬 아티팩트 있을 때만 — 보너스).

    가짜 태거 테스트가 계약을 이미 보증하므로 여기서는 로드·채점이 실제
    아티팩트로도 성립하는지만 본다.
    """
    from models.layer3 import score_from_trades

    out = score_from_trades(synthetic_trades, price_df=price_df, index_df=index_df)
    _assert_contract(out, len(synthetic_trades))
