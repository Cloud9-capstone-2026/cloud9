"""
detect.py 순수 함수 스모크 — DB·네트워크 없이 표준화 → 신규 추출 → 판정
배관이 계약대로 동작함을 보증한다 (비동기 전환으로 이 배관이 worker로 이사).
run_pipeline_from_db 자체(DB 세션 필요)는 test_analysis_jobs가 job 단위로 커버.

판정 계약: 계층별 독립 flag(rule=위반 존재, stat=마할라노비스>2.5,
deep=점수>=DEEP_THRESHOLD) → flag 개수 0/1/2+ = 정상/경고/이상.
"""

import pandas as pd
import pytest

from models.rule_based import run_rule_based
from models.zscore import run_zscore
from pipeline.detect import DEEP_THRESHOLD, _build_ensemble, _extract_new_trades


def test_extract_first_upload_returns_all(standard_trades):
    """baseline 비어있음(첫 업로드) → 전체가 신규, 위치는 0..n-1."""
    empty = pd.DataFrame(columns=standard_trades.columns)
    new, pos = _extract_new_trades(empty, standard_trades)
    assert len(new) == len(standard_trades)
    assert list(pos) == list(range(len(standard_trades)))


def test_extract_dedup_returns_only_new(standard_trades):
    """이전 업로드에 있던 5건 제외 → 신규 3건, new_df 내 위치 보존."""
    baseline = standard_trades.head(5)
    new, pos = _extract_new_trades(baseline, standard_trades)
    assert len(new) == 3
    assert list(pos) == [5, 6, 7]
    pd.testing.assert_frame_equal(
        new.reset_index(drop=True),
        standard_trades.tail(3).reset_index(drop=True),
    )


def test_rule_and_stat_shapes(standard_trades):
    """1·2계층 실행 스모크 — 행 수·키 계약 (픽스처 8건, 규칙 위반 없음)."""
    rule = run_rule_based(standard_trades)
    stat = run_zscore(standard_trades, standard_trades.head(5))
    assert len(rule["trade_results"]) == len(standard_trades)
    assert len(stat["trade_results"]) == len(standard_trades)
    for r in rule["trade_results"]:
        assert set(r) >= {"날짜", "종목명", "rule_score", "triggered_rules"}
        assert 0.0 <= r["rule_score"] <= 1.0
    for s in stat["trade_results"]:
        assert set(s) >= {"날짜", "종목명", "stat_score", "mahalanobis"}
        assert 0.0 <= s["stat_score"] <= 1.0


# ─ 판정(verdict) 계약 — 계층 결과를 손으로 구성해 조합별로 검증 ─

def _rule_row(triggered):
    return {"날짜": "2020-06-01", "종목명": "테스트A",
            "rule_score": 0.7 if triggered else 0.0,
            "triggered_rules": ["당일_왕복매매"] if triggered else []}


def _stat_row(anomalous, m=None):
    if m is None:
        m = 3.1 if anomalous else 1.2
    return {"날짜": "2020-06-01", "종목명": "테스트A", "z_vector": [0, 0, 0],
            "mahalanobis": m, "stat_score": 0.7 if anomalous else 0.3,
            "is_anomaly": anomalous}


def _deep_row(score):
    return {"score": score, "top_bias": "disposition_strength",
            "top_bias_명": "처분효과",
            "bias_scores": {"disposition_strength": score, "overconfidence": 0.1,
                            "lottery_preference": 0.1, "herd_sensitivity": 0.1}}


def _one(rule_on, stat_on, deep_score):
    """계층 판정 1거래 구성 → ensemble 1행 반환."""
    rule = {"is_anomaly": rule_on, "trade_results": [_rule_row(rule_on)]}
    stat = {"is_anomaly": stat_on, "trade_results": [_stat_row(stat_on)]}
    rows = None if deep_score is None else [_deep_row(deep_score)]
    return _build_ensemble(rule, stat, rows)[0]


HI = DEEP_THRESHOLD + 0.01   # deep flag 켜지는 점수
LO = DEEP_THRESHOLD - 0.01   # 안 켜지는 점수


@pytest.mark.parametrize("rule_on,stat_on,deep_score,want", [
    (False, False, LO, "정상"),   # flag 0개
    (True,  False, LO, "경고"),   # rule만
    (False, True,  LO, "경고"),   # stat만
    (False, False, HI, "경고"),   # deep만
    (True,  True,  LO, "이상"),   # 2개
    (True,  False, HI, "이상"),
    (True,  True,  HI, "이상"),   # 3개
])
def test_verdict_mapping(rule_on, stat_on, deep_score, want):
    e = _one(rule_on, stat_on, deep_score)
    assert e["verdict"] == want
    assert e["flags"] == {"rule": rule_on, "stat": stat_on,
                          "deep": deep_score >= DEEP_THRESHOLD}
    assert e["layers_available"] == 3


@pytest.mark.parametrize("rule_on,stat_on,want", [
    (False, False, "정상"),
    (True,  False, "경고"),
    (True,  True,  "이상"),   # 2계층만으로도 "이상" 가능
])
def test_verdict_without_deep_layer(rule_on, stat_on, want):
    """3계층 판정 불가(절단 밖·실패) — 두 계층만으로 같은 규칙 적용."""
    e = _one(rule_on, stat_on, None)
    assert e["verdict"] == want
    assert e["layers_available"] == 2
    assert "deep" not in e["flags"]
    assert e["deep"] is None


def test_deep_flag_theta_boundary():
    """θ 경계: 정확히 θ면 flag(이상 신호는 포함 판정), 그 아래면 미flag."""
    assert _one(False, False, DEEP_THRESHOLD)["flags"]["deep"] is True
    assert _one(False, False, DEEP_THRESHOLD - 1e-6)["flags"]["deep"] is False


def test_ensemble_row_contract():
    """프론트 계약 필드 — 키·타입·계층별 상세 재료."""
    e = _one(True, False, HI)
    assert set(e) == {"날짜", "종목명", "verdict", "flags", "layers_available",
                      "rule", "stat", "deep"}
    assert e["rule"]["triggered_rules"] == ["당일_왕복매매"]
    assert isinstance(e["stat"]["mahalanobis"], float)
    assert e["deep"]["top_bias_명"] == "처분효과"
    assert set(e["deep"]["bias_scores"]) == {
        "disposition_strength", "overconfidence",
        "lottery_preference", "herd_sensitivity"}


def test_deep_evidence_passthrough():
    """layer3가 계산한 evidence(판정 근거)는 deep에 그대로 실린다 — 없으면 None."""
    ev = {"disposition_strength": {
        "trade_share": 0.62, "context_share": 0.38,
        "features": [{"feature": "보유기간", "attribution": 0.42}]}}
    rule = {"is_anomaly": False, "trade_results": [_rule_row(False)]}
    stat = {"is_anomaly": False, "trade_results": [_stat_row(False)]}
    e = _build_ensemble(rule, stat, [{**_deep_row(HI), "evidence": ev}])[0]
    assert e["deep"]["evidence"] == ev
    assert _one(False, False, HI)["deep"]["evidence"] is None  # 계산 실패 행


def test_db_write_includes_deep_details(monkeypatch, tmp_path, standard_trades):
    """DB 저장(xai_result)에 딥러닝 상세가 포함된다 — top_bias_명·bias_scores·
    evidence. 조회 라우터(GET /analysis/)는 저장분을 그대로 반환하므로 이
    계약이 곧 프론트가 받는 형태다. sqlite 인메모리 + 가짜 3계층."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    import orm
    from database import Base
    from pipeline import detect

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()

    db.add(orm.CsvUpload(id=1, file_name="t.csv"))
    for _, r in standard_trades.iterrows():
        db.add(orm.Trade(
            upload_id=1, 거래일자=r["날짜"].date(), 종목명=r["종목명"],
            거래구분=r["매매구분"], 거래수량=int(r["체결수량"]),
            거래단가=int(r["체결단가"]), 거래금액=int(r["총거래금액"]),
            수수료=0, 거래세=0, 정산금액=int(r["총거래금액"]),
        ))
    db.commit()

    EVID = {"disposition_strength": {
        "trade_share": 0.61, "context_share": 0.39,
        "features": [{"feature": "매도실현수익률", "attribution": -1.2}]}}

    def fake_layer3(df, user_id="user"):
        return {
            "per_trade": [{
                "row": i, "trade_score": 0.9,
                "top_bias": "disposition_strength", "top_bias_명": "처분효과",
                "bias_scores": {"disposition_strength": 0.9, "overconfidence": 0.1,
                                "lottery_preference": 0.1, "herd_sensitivity": 0.1},
                "evidence": EVID,
            } for i in range(len(df))],
            "lstm_score": 0.9, "bias_mean": {}, "n_events": len(df),
            "account_metrics": None,
        }

    monkeypatch.setattr(detect, "layer3_score", fake_layer3)
    # 지표 계산은 실코드가 시세 조회를 타므로 차단 — 점검 unavailable 경로로
    monkeypatch.setattr(detect, "layer3_metrics", lambda df, user_id="u": None)
    monkeypatch.setattr(detect, "REPORTS_DIR", tmp_path)  # 리포트 파일은 임시로

    detect.run_pipeline_from_db(db, upload_id=1, Trade=orm.Trade,
                                AnalysisResult=orm.AnalysisResult,
                                user_id="user_001")

    rows = db.query(orm.AnalysisResult).all()
    assert len(rows) == len(standard_trades)
    for r in rows:
        x = r.xai_result
        assert x["top_bias_명"] == "처분효과"
        assert set(x["bias_scores"]) == {"disposition_strength", "overconfidence",
                                         "lottery_preference", "herd_sensitivity"}
        assert x["evidence"] == EVID
        assert x["deep_excluded"] is False  # 미발동 계좌 — 필드는 항상 존재
        assert r.lstm_score == 0.9
        assert r.upload_id == 1


def test_pipeline_baseline_scoped_to_upload_owner(monkeypatch, tmp_path,
                                                  standard_trades):
    """분석 기준선(이전 거래)은 업로드 주인 것만 본다.

    사용자 A가 올린 것과 동일한 거래를 사용자 B가 올려도 B에게는 전부
    신규여야 한다 — 스코핑이 없으면 타인 거래에 걸려 신규 0건이 된다
    (저장 쪽 사용자 범위 중복 체크와 대칭인, 읽기 쪽 회귀 감시).
    같은 사용자의 재업로드 중복 스킵은 그대로 유지되는지도 함께 확인."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    import orm
    from database import Base
    from pipeline import detect

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()

    def add_upload(upload_id, user_id):
        db.add(orm.CsvUpload(id=upload_id, file_name=f"{upload_id}.csv",
                             user_id=user_id))
        for _, r in standard_trades.iterrows():
            db.add(orm.Trade(
                upload_id=upload_id, user_id=user_id,
                거래일자=r["날짜"].date(), 종목명=r["종목명"],
                거래구분=r["매매구분"], 거래수량=int(r["체결수량"]),
                거래단가=int(r["체결단가"]), 거래금액=int(r["총거래금액"]),
                수수료=0, 거래세=0, 정산금액=int(r["총거래금액"]),
            ))
        db.commit()

    add_upload(1, user_id=1)  # 사용자 A
    add_upload(2, user_id=2)  # 사용자 B — A와 완전히 동일한 거래

    monkeypatch.setattr(detect, "layer3_score", None)  # 신규 추출만 검증
    monkeypatch.setattr(detect, "REPORTS_DIR", tmp_path)

    out_b = detect.run_pipeline_from_db(db, upload_id=2, Trade=orm.Trade,
                                        AnalysisResult=orm.AnalysisResult,
                                        user_id="user_002")
    assert out_b["new_trades_count"] == len(standard_trades)  # 전부 B의 신규

    add_upload(3, user_id=1)  # 사용자 A가 같은 내용을 재업로드
    out_a = detect.run_pipeline_from_db(db, upload_id=3, Trade=orm.Trade,
                                        AnalysisResult=orm.AnalysisResult,
                                        user_id="user_001")
    assert out_a["new_trades_count"] == 0  # 본인 이력에는 걸림 — 중복 스킵 유지
    db.close()


def _pipeline_env(monkeypatch, tmp_path, standard_trades):
    """sqlite + 단일 사용자 업로드 1건 — 분포 점검 v2 배선 테스트 공용 준비."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    import orm
    from database import Base
    from pipeline import detect

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()
    db.add(orm.CsvUpload(id=1, file_name="t.csv", user_id=1))
    for _, r in standard_trades.iterrows():
        db.add(orm.Trade(
            upload_id=1, user_id=1, 거래일자=r["날짜"].date(), 종목명=r["종목명"],
            거래구분=r["매매구분"], 거래수량=int(r["체결수량"]),
            거래단가=int(r["체결단가"]), 거래금액=int(r["총거래금액"]),
            수수료=0, 거래세=0, 정산금액=int(r["총거래금액"]),
        ))
    db.commit()
    monkeypatch.setattr(detect, "REPORTS_DIR", tmp_path)
    return db, orm, detect


def test_distribution_trigger_skips_deep_scoring(monkeypatch, tmp_path,
                                                 standard_trades):
    """분포 점검 발동(deep_excluded) 계좌 — 3계층 채점(XAI 포함)이 호출조차
    되지 않고, 전 거래가 2계층 판정(deep null), 플래그가 응답·DB에 실린다."""
    db, orm, detect = _pipeline_env(monkeypatch, tmp_path, standard_trades)

    monkeypatch.setattr(detect, "layer3_metrics",
                        lambda df, user_id="u": {"turnover_annual": 99999.0})
    monkeypatch.setattr(detect, "check_distribution", lambda m: {
        "status": "out_of_range", "deep_excluded": True,
        "out_of_range": {"turnover_annual": {"value": 99999.0}}})

    def never_called(*a, **k):
        raise AssertionError("발동 계좌에서 3계층 채점이 호출되면 안 됨")
    monkeypatch.setattr(detect, "layer3_score", never_called)

    result = detect.run_pipeline_from_db(db, upload_id=1, Trade=orm.Trade,
                                         AnalysisResult=orm.AnalysisResult,
                                         user_id="user_001")
    assert result["distribution_check"]["deep_excluded"] is True
    for e in result["detection_result"]["ensemble"]:
        assert e["deep"] is None            # 거래별 딥러닝 판정 없음
        assert e["layers_available"] == 2   # 규칙+통계만
    for r in db.query(orm.AnalysisResult).all():
        assert r.lstm_score is None
        # 프론트가 주의 문구를 띄울 유일한 신호 — 행마다 저장돼야 한다
        assert r.xai_result["deep_excluded"] is True
    db.close()


def test_distribution_ok_proceeds_to_deep(monkeypatch, tmp_path, standard_trades):
    """미발동 계좌 — 3계층 채점이 정확히 1회 호출된다 (게이트 통과 회귀)."""
    db, orm, detect = _pipeline_env(monkeypatch, tmp_path, standard_trades)

    monkeypatch.setattr(detect, "layer3_metrics",
                        lambda df, user_id="u": {"n_trades": 8.0})
    monkeypatch.setattr(detect, "check_distribution", lambda m: {
        "status": "ok", "deep_excluded": False, "out_of_range": {}})

    calls = []

    def spy_score(df, user_id="u"):
        calls.append(len(df))
        return None  # 채점 실패 폴백 경로 — 여기서는 호출 여부만 검증

    monkeypatch.setattr(detect, "layer3_score", spy_score)
    result = detect.run_pipeline_from_db(db, upload_id=1, Trade=orm.Trade,
                                         AnalysisResult=orm.AnalysisResult,
                                         user_id="user_001")
    assert calls == [len(standard_trades)]  # 전체 이력으로 1회 채점
    assert result["distribution_check"]["deep_excluded"] is False
    db.close()


def test_pipeline_applies_user_ruleset(monkeypatch, tmp_path, standard_trades):
    """사용자 등록 규칙이 파이프라인 끝까지 흐른다 — ensemble의
    triggered_rules와 DB 저장(xai_result)에 사용자 규칙명이 실린다."""
    db, orm, detect = _pipeline_env(monkeypatch, tmp_path, standard_trades)
    monkeypatch.setattr(detect, "layer3_score", None)  # 3계층 무관
    # 사용자가 "1회 매수금액 상한 1원"을 등록한 상황 — 모든 매수가 걸린다
    monkeypatch.setattr(detect, "load_ruleset",
                        lambda db_, uid: [("single_buy_cap", 1)])

    result = detect.run_pipeline_from_db(db, upload_id=1, Trade=orm.Trade,
                                         AnalysisResult=orm.AnalysisResult,
                                         user_id="user_001")
    ens = result["detection_result"]["ensemble"]
    buys = [e for e in ens if "매수금액_상한" in e["rule"]["triggered_rules"]]
    assert buys  # 매수 거래들이 사용자 규칙에 걸림
    for e in ens:
        assert "일중_반복매매" not in e["rule"]["triggered_rules"]  # 기본 조합 미사용
    stored = [r.xai_result["triggered_rules"]
              for r in db.query(orm.AnalysisResult).all()]
    assert any("매수금액_상한" in t for t in stored)  # 프론트 경로까지 도달
    db.close()


def test_stat_flag_follows_zscore_definition(standard_trades):
    """stat flag는 zscore의 거래별 is_anomaly(마할라노비스>2.5)를 그대로 따른다."""
    rule = run_rule_based(standard_trades)
    stat = run_zscore(standard_trades, standard_trades.head(5))
    ens = _build_ensemble(rule, stat, None)
    for e, s in zip(ens, stat["trade_results"]):
        assert e["flags"]["stat"] == s["is_anomaly"]
        assert e["stat"]["mahalanobis"] == s["mahalanobis"]
