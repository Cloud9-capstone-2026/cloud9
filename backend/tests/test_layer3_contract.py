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


def test_account_metrics_standalone_matches_scoring_path(
        fake_layer3, no_network_layer3, standard_trades):
    """분포 점검 v2 — 채점 전에 지표만 뽑는 account_metrics()가 채점 경로의
    account_metrics와 완전히 일치해야 한다. 같은 변환·피처 코드를 공유하므로
    산식이 갈라지면 여기서 걸린다."""
    scored = fake_layer3.score_account(standard_trades, user_id="tester")
    metrics = fake_layer3.account_metrics(standard_trades, user_id="tester")
    assert scored is not None and metrics is not None
    assert metrics == scored["account_metrics"]


def test_account_metrics_needs_no_model(no_network_layer3, monkeypatch,
                                        standard_trades):
    """account_metrics는 모델 아티팩트 없이 동작 — 모델 미설정 서버에서도
    분포 점검(v2 발동 판단)이 가능해야 한다."""
    from models import layer3

    def no_model():
        raise AssertionError("account_metrics가 모델을 로드하면 안 됨")

    monkeypatch.setattr(layer3, "_load_artifacts", no_model)
    m = layer3.account_metrics(standard_trades, user_id="tester")
    assert m is not None and m["n_trades"] == len(standard_trades)


def test_per_trade_evidence_contract(fake_layer3, synthetic_trades,
                                     price_df, index_df):
    """XAI 근거(evidence) 계약 — 편향 4종 각각 기여율 분해 + 피처별 기여.

    trade_share·context_share는 |현재 거래 기여|와 |과거 문맥 기여|의 비율
    (합 1, 반올림 오차 허용). features는 값 채널 10개 전부 — 관측여부 채널은
    결측 표현용 내부 구조라 미노출. 표시명 + 로짓 단위 기여도(부호 유지),
    |기여| 내림차순.
    """
    out = fake_layer3.score_from_trades(
        synthetic_trades, price_df=price_df, index_df=index_df
    )
    for e in out["per_trade"]:
        ev = e["evidence"]
        assert set(ev) == BIAS_PARAMS
        for d in ev.values():
            assert set(d) == {"trade_share", "context_share", "features"}
            if d["trade_share"] is not None:
                assert d["trade_share"] + d["context_share"] == \
                    pytest.approx(1.0, abs=0.02)
            feats = d["features"]
            assert len(feats) == 10  # 값 채널 전부
            assert all(set(f) == {"feature", "attribution"} for f in feats)
            assert all("(관측)" not in f["feature"] for f in feats)
            mags = [abs(f["attribution"]) for f in feats]
            assert mags == sorted(mags, reverse=True)

    # 시퀀스 첫 거래는 과거 문맥이 없다 — 기여율이 현재 거래 100%
    first = out["per_trade"][0]
    for d in first["evidence"].values():
        assert d["context_share"] in (0.0, None)


@pytest.fixture()
def tiny_window_layer3(fake_layer3, monkeypatch):
    """가짜 태거의 창 크기(max_len)를 6으로 줄여 8건 픽스처가 창 분할
    경로(N > W)를 타게 한다. 모델·정규화 통계는 fake_layer3 그대로."""
    model, meta = fake_layer3._load_artifacts()
    monkeypatch.setattr(fake_layer3, "_load_artifacts",
                        lambda: (model, {**meta, "max_len": 6}))
    return fake_layer3


def test_long_history_scores_all_trades(tiny_window_layer3, synthetic_trades,
                                        price_df, index_df):
    """이력이 창(max_len)보다 길어도 전 거래가 채점된다 — 창 보폭 1 폴백.

    과거에는 최근 max_len건만 채점하고 나머지는 deep 없이 2계층 폴백이었다.
    """
    out = tiny_window_layer3.score_from_trades(
        synthetic_trades, price_df=price_df, index_df=index_df
    )
    _assert_contract(out, len(synthetic_trades))  # 8건 > 창 6 — 행 1:1 유지
    assert all("evidence" in e for e in out["per_trade"])


def test_window_scores_match_manual_slices(tiny_window_layer3, synthetic_trades,
                                           price_df, index_df):
    """창 규약 검증 — 같은 정규화 시퀀스로 손수 채점한 값과 일치.

    위치 t < W: 첫 창 [0, W)의 위치 t 점수.
    위치 t >= W: 창 [t-W+1, t]을 단독 채점한 마지막 위치 점수.
    """
    import torch

    W = 6
    out = tiny_window_layer3.score_from_trades(
        synthetic_trades, price_df=price_df, index_df=index_df
    )
    model, meta = tiny_window_layer3._load_artifacts()
    params = [meta["attr_param"][a] for a in meta["attrs"]]

    # layer3와 같은 경로로 정규화 시퀀스 재구성
    from synthetic_data.features import build_features
    from ml import seqfeat
    trades = synthetic_trades.reset_index(drop=True)
    fout = build_features(trades, price_df, index_df, windows=(None,))
    ev = seqfeat.attach_trade_rows(fout["events"], trades)
    feat = seqfeat.event_features(ev)
    _, X, lengths, rows = seqfeat.build_sequences(
        feat, meta["norm_stats"], len(feat), return_rows=True
    )
    N = int(lengths[0])
    M = torch.from_numpy(X[0, :N])
    by_row = {e["row"]: e for e in out["per_trade"]}

    with torch.no_grad():
        first = torch.sigmoid(model(M[:W].unsqueeze(0), torch.tensor([W])))[0]
        for t in range(W):                       # 첫 창 구간
            got = by_row[int(rows[0, t])]["bias_scores"]
            for j, p in enumerate(params):
                assert got[p] == pytest.approx(float(first[t, j]), abs=1e-4)
        for t in range(W, N):                    # 꼬리 창 구간
            win = M[t - W + 1: t + 1].unsqueeze(0)
            want = torch.sigmoid(model(win, torch.tensor([W])))[0, W - 1]
            got = by_row[int(rows[0, t])]["bias_scores"]
            for j, p in enumerate(params):
                assert got[p] == pytest.approx(float(want[j]), abs=1e-4)


def test_no_market_data_trades_not_scored(fake_layer3, synthetic_trades,
                                          price_df, index_df):
    """시세가 전혀 없는 종목의 거래는 채점 제외 — "시세 조회 실패"라는 시스템
    사정이 결측 신호로 점수에 들어가지 않도록. 제외 거래는 detect.py에서
    2계층 판정으로 폴백되고, 나머지 거래는 정상 채점된다."""
    partial = price_df[price_df["종목코드"] != "000030"]
    out = fake_layer3.score_from_trades(
        synthetic_trades, price_df=partial, index_df=index_df
    )
    tr = synthetic_trades.reset_index(drop=True)
    dropped = set(tr.index[tr["종목코드"] == "000030"])
    assert dropped, "픽스처에 000030 거래가 있어야 하는 테스트"

    rows = {e["row"] for e in out["per_trade"]}
    assert rows == set(range(len(tr))) - dropped
    assert out["n_events"] == len(tr) - len(dropped)
    assert all("evidence" in e for e in out["per_trade"])  # 채점분은 근거도 정상


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
