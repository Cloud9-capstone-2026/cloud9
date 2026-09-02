"""
비동기 전환 검증 — sqlite 인메모리 + TestClient, 외부 네트워크·실분석·실LLM 0.

분석 파이프라인은 mock 카운터로, CSV 매핑(LLM)은 표준 CSV를 그대로 읽는
가짜 map_file로 대체. TestClient는 BackgroundTasks를 응답 직후 동기로
실행하므로 업로드 → worker(매핑 → 거래 저장 → 분석) 완주까지 한 요청 안에서
검증. 원본 파일 저장 위치는 tmp_path로 격리.

[JWT 도입 관련 수정 — 2026-08-17]
get_db와 같은 방식으로 get_current_user도 override한다. 실제 로그인 플로우를
타지 않고 고정된 가짜 유저(app_env["current_user_id"]로 조작 가능)를 반환 —
이 파일이 검증하려는 건 업로드→worker 완주, job 소유권 로직이지 인증 로직
자체가 아니므로 이 방식이 적절함.
"""

import io

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture()
def app_env(monkeypatch):
    """인메모리 DB로 앱 구성 + worker 세션·파이프라인·매핑을 테스트용으로 주입."""
    import database
    from database import Base

    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # 인메모리 공유 — 모든 세션이 같은 DB를 봄
    )
    TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    import orm  # noqa: F401 — 테이블 정의 등록
    Base.metadata.create_all(bind=engine)

    from pipeline import jobs as jobs_mod
    from pipeline import upload_store

    session_count = {"n": 0}

    def counting_session():
        session_count["n"] += 1
        return TestSession()

    monkeypatch.setattr(jobs_mod, "SessionLocal", counting_session)

    map_calls = []

    def fake_map(raw, filename):
        """표준 CSV를 그대로 변환 결과로 — 실LLM 없이 매핑 단계 통과."""
        map_calls.append(filename)
        df = pd.read_csv(io.BytesIO(raw))
        df["거래일자"] = pd.to_datetime(df["거래일자"])
        return df

    monkeypatch.setattr(jobs_mod, "map_file", fake_map)

    pipeline_calls = []

    def fake_pipeline(db, upload_id, Trade, AnalysisResult, user_id="user_001", job_id=None):
        pipeline_calls.append(upload_id)
        return {"new_trades_count": 0, "detection_result": {"ensemble": []}}

    monkeypatch.setattr(jobs_mod, "run_pipeline_from_db", fake_pipeline)

    from main import app
    from database import get_db
    from auth import get_current_user

    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    # [JWT 도입] 기본 로그인 유저 id=1. current_user_id["id"]를 바꾸면
    # 다음 요청부터 다른 유저로 인증된 것처럼 동작 (소유권 테스트용).
    current_user_id = {"id": 1}

    class _FakeUser:
        @property
        def id(self):
            return current_user_id["id"]

    def override_get_current_user():
        return _FakeUser()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    client = TestClient(app)
    yield {"client": client, "Session": TestSession,
           "pipeline_calls": pipeline_calls, "session_count": session_count,
           "map_calls": map_calls, "upload_store": upload_store,
           "current_user_id": current_user_id}
    app.dependency_overrides.clear()


CSV = (
    "거래일자,종목명,거래구분,거래수량,거래단가,거래금액,수수료,거래세,정산금액\n"
    "2020-06-01,테스트A,매수,10,10000,100000,0,0,100000\n"
    "2020-06-03,테스트A,매도,10,11000,110000,0,0,110000\n"
)


def _upload(client, body=CSV):
    return client.post("/trades/upload",
                       files={"file": ("t.csv", io.BytesIO(body.encode("utf-8-sig")),
                                       "text/csv")})


def test_upload_contract_and_worker_completion(app_env):
    """202 + job_id 즉시 반환(status=pending), analysis 필드 없음.
    TestClient가 백그라운드를 이어 돌리므로 최종적으로 job은 done이고,
    거래 저장은 업로드 응답이 아니라 worker(매핑 후)가 수행한다."""
    r = _upload(app_env["client"])
    assert r.status_code == 202
    body = r.json()
    assert set(body) >= {"upload_id", "job_id", "status", "message"}
    assert body["status"] == "pending"  # 응답 시점 = 매핑·분석 시작 전
    assert "analysis" not in body       # 구 계약 필드 제거
    assert "건 저장" not in body["message"]  # 건수는 매핑 전이라 알 수 없음

    # [2026-08-27] DB 저장(orm.UploadFile) 도입으로 매핑에 넘어가는 파일명이
    # 실제 원본 파일명(csv_uploads.file_name, 여기선 "t.csv")으로 바뀜.
    # 예전 디스크 저장 방식은 원본 파일명을 버리고 "{upload_id}.csv"로 덮어
    #썼었는데, 이건 원본 파일명이 조용히 유실되던 부작용이었고 DB 방식이
    # 오히려 이를 올바르게 보존하는 동작이라 이 값이 맞다.
    assert app_env["map_calls"] == ["t.csv"]  # 매핑 1회, 원본 파일명 그대로
    assert app_env["pipeline_calls"] == [body["upload_id"]]      # 분석 1회
    from orm import AnalysisJob, CsvUpload, Trade
    db = app_env["Session"]()
    job = db.query(AnalysisJob).filter(AnalysisJob.id == body["job_id"]).one()
    assert job.status == "done"
    assert job.started_at is not None and job.finished_at is not None
    assert db.query(Trade).count() == 2  # worker가 매핑 결과를 저장했음
    up = db.query(CsvUpload).filter(CsvUpload.id == body["upload_id"]).one()
    assert up.status == "done" and up.row_count == 2
    db.close()


def test_upload_saves_raw_file(app_env):
    """원본 파일이 그대로 남는다 — worker·재시도·실패 조사의 재료.

    [2026-08-27] orm.UploadFile 테이블 추가로 upload_store가 DB 저장을
    우선하게 됨(디스크는 테이블 없을 때만 쓰는 폴백) — 그래서 find_upload
    (디스크 전용 조회)가 아니라 upload_store.load_upload(DB 우선, 없으면
    디스크)로 확인해야 실제 저장 위치와 무관하게 검증 가능."""
    r = _upload(app_env["client"])
    uid = r.json()["upload_id"]

    db = app_env["Session"]()
    loaded = app_env["upload_store"].load_upload(uid, db)
    db.close()

    assert loaded is not None
    raw, filename = loaded
    assert raw == CSV.encode("utf-8-sig")


def test_upload_rejects_unknown_extension(app_env):
    r = app_env["client"].post(
        "/trades/upload",
        files={"file": ("notes.txt", io.BytesIO(b"hello"), "text/plain")})
    assert r.status_code == 400


def test_mapping_failure_fails_job_without_trades(app_env, monkeypatch):
    """매핑 실패 → job failed, 거래 미저장(전부 아니면 전무), 원본 파일 존치."""
    from pipeline import jobs as jobs_mod
    from pipeline.csv_mapper import MappingError

    def bad_map(raw, filename):
        raise MappingError("필수 필드 매핑 없음: ['거래일자']")

    monkeypatch.setattr(jobs_mod, "map_file", bad_map)
    r = _upload(app_env["client"])
    body = r.json()

    from orm import AnalysisJob, CsvUpload, Trade
    db = app_env["Session"]()
    job = db.query(AnalysisJob).filter(AnalysisJob.id == body["job_id"]).one()
    assert job.status == "failed"
    assert "필수 필드" in job.error_reason           # 내부 기록
    assert db.query(Trade).count() == 0              # 아무것도 저장 안 됨
    up = db.query(CsvUpload).filter(CsvUpload.id == body["upload_id"]).one()
    assert up.status == "failed"
    db.close()
    assert app_env["pipeline_calls"] == []           # 분석까지 안 감
    db2 = app_env["Session"]()
    assert app_env["upload_store"].load_upload(body["upload_id"], db2) is not None
    db2.close()

def test_reupload_skips_duplicate_trades(app_env):
    """같은 파일 재업로드 — 5컬럼 키 개수 대조로 전 행 상쇄, 이중 저장 없음."""
    from orm import CsvUpload, Trade

    _upload(app_env["client"])
    r2 = _upload(app_env["client"])
    db = app_env["Session"]()
    assert db.query(Trade).count() == 2  # 두 번 올려도 거래는 한 벌
    up2 = db.query(CsvUpload).filter(
        CsvUpload.id == r2.json()["upload_id"]).one()
    assert up2.status == "done" and up2.row_count == 0  # 신규 0건
    db.close()


# 분할 체결·같은 날 동일 조건 재거래 — 5키가 완전히 같은 진짜 거래 여러 건.
# 존재 여부 판정 시절엔 첫 건만 남고 유실됐다(2026-09-02 개수 대조로 수리).
CSV_SPLIT = (
    "거래일자,종목명,거래구분,거래수량,거래단가,거래금액,수수료,거래세,정산금액\n"
    "2020-06-01,테스트A,매수,10,10000,100000,0,0,100000\n"
    "2020-06-01,테스트A,매수,10,10000,100000,0,0,100000\n"
    "2020-06-03,테스트A,매도,10,11000,110000,0,0,110000\n"
)


def test_split_fills_all_saved(app_env):
    """한 파일 안의 동일 5키 2행 — 둘 다 실거래로 저장된다."""
    from orm import CsvUpload, Trade

    r = _upload(app_env["client"], body=CSV_SPLIT)
    db = app_env["Session"]()
    assert db.query(Trade).count() == 3
    buys = db.query(Trade).filter(Trade.거래구분 == "매수").count()
    assert buys == 2  # 분할 체결 2건 모두 보존
    up = db.query(CsvUpload).filter(CsvUpload.id == r.json()["upload_id"]).one()
    assert up.row_count == 3
    db.close()
    # 분석도 전 행을 신규로 받는다 (신규 판정은 저장이 유일 책임)
    assert app_env["pipeline_calls"] == [r.json()["upload_id"]]


def test_partial_overlap_saves_only_excess(app_env):
    """기존 업로드와 일부 겹치는 파일 — 키별 '늘어난 개수'만 신규 저장.

    1차: 매수 1 + 매도 1 저장. 2차(CSV_SPLIT): 같은 매수 2 + 같은 매도 1 —
    매수는 기존 1건과 상쇄돼 1건만, 매도는 전량 상쇄. 신규 1건."""
    from orm import CsvUpload, Trade

    _upload(app_env["client"])                      # CSV: 매수 1 + 매도 1
    r2 = _upload(app_env["client"], body=CSV_SPLIT)
    db = app_env["Session"]()
    assert db.query(Trade).count() == 3             # 2 + 신규 1
    assert db.query(Trade).filter(Trade.거래구분 == "매수").count() == 2
    up2 = db.query(CsvUpload).filter(CsvUpload.id == r2.json()["upload_id"]).one()
    assert up2.row_count == 1
    db.close()


def test_unique_upload_id_constraint(app_env):
    """같은 upload_id로 job 2개 → DB unique 제약이 거부."""
    from sqlalchemy.exc import IntegrityError
    from orm import AnalysisJob, CsvUpload

    db = app_env["Session"]()
    up = CsvUpload(file_name="x.csv")
    db.add(up)
    db.flush()
    db.add(AnalysisJob(upload_id=up.id))
    db.commit()
    db.add(AnalysisJob(upload_id=up.id))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
    db.close()


def test_conditional_claim_prevents_double_run(app_env):
    """pending이 아닌 job은 worker가 잡지 못함 — 분석 중복 실행 0회."""
    from pipeline.jobs import run_analysis_job
    from orm import AnalysisJob, CsvUpload

    db = app_env["Session"]()
    up = CsvUpload(file_name="x.csv")
    db.add(up)
    db.flush()
    job = AnalysisJob(upload_id=up.id, status="pending")
    db.add(job)
    db.commit()
    jid = job.id
    # worker가 읽을 원본도 준비 (라우트를 거치지 않고 job을 만들었으므로)
    app_env["upload_store"].save_upload(up.id, CSV.encode("utf-8-sig"), db)
    db.commit()
    db.close()

    run_analysis_job(jid)                       # 정상 1회 실행 → done
    assert len(app_env["pipeline_calls"]) == 1
    run_analysis_job(jid)                       # done 상태 재청구 → 거부
    assert len(app_env["pipeline_calls"]) == 1  # 추가 실행 없음

    db = app_env["Session"]()
    assert db.query(AnalysisJob).filter(AnalysisJob.id == jid).one().status == "done"
    db.close()


def test_invalid_transition_rejected(app_env):
    """running(다른 worker 소유)·failed 상태도 재청구 불가 — 전이 규칙 검증."""
    from pipeline.jobs import run_analysis_job
    from orm import AnalysisJob, CsvUpload

    db = app_env["Session"]()
    for status in ("running", "failed"):
        up = CsvUpload(file_name=f"{status}.csv")
        db.add(up)
        db.flush()
        job = AnalysisJob(upload_id=up.id, status=status)
        db.add(job)
        db.commit()
        run_analysis_job(job.id)
        db.expire_all()
        assert job.status == status         # 상태 불변
    assert app_env["pipeline_calls"] == []  # 분석 실행 0회
    db.close()


def test_recover_stale_jobs_cleans_orphans(app_env):
    """서버 재시작 시나리오 — 기동 정리(recover_stale_jobs)가 running·pending
    잔존 job을 failed로 바꾸고, 그 업로드가 만들다 만 산출물(거래·분석 결과)을
    지워 재업로드가 첫 업로드처럼 돌게 한다. done 업로드는 전부 불변."""
    from datetime import date

    from pipeline.jobs import recover_stale_jobs
    from orm import AnalysisJob, AnalysisResult, CsvUpload, Trade

    def _trade(uid):
        return Trade(upload_id=uid, 거래일자=date(2020, 6, 1), 종목명="테스트A",
                     거래구분="매수", 거래수량=1, 거래단가=100, 거래금액=100,
                     수수료=0, 거래세=0, 정산금액=100)

    db = app_env["Session"]()
    ids = {}
    for status in ("running", "pending", "done"):
        up = CsvUpload(file_name=f"{status}.csv", row_count=1)
        db.add(up)
        db.flush()
        db.add(AnalysisJob(upload_id=up.id, status=status))
        # 저장까지 진행된 흔적 — running은 지워져야, done은 남아야 한다
        db.add(_trade(up.id))
        db.add(AnalysisResult(upload_id=up.id, detail={}))
        db.commit()
        ids[status] = up.id
    db.close()

    assert recover_stale_jobs() == 2  # running + pending만

    db = app_env["Session"]()
    for status in ("running", "pending"):
        uid = ids[status]
        job = db.query(AnalysisJob).filter(AnalysisJob.upload_id == uid).one()
        assert job.status == "failed"
        assert "재시작" in job.error_reason      # 내부 기록
        assert job.finished_at is not None
        up = db.query(CsvUpload).filter(CsvUpload.id == uid).one()
        assert up.status == "failed"
        assert up.row_count is None              # 산출물 제거로 건수 무효
        assert db.query(Trade).filter(Trade.upload_id == uid).count() == 0
        assert db.query(AnalysisResult).filter(
            AnalysisResult.upload_id == uid).count() == 0
    done_uid = ids["done"]
    assert db.query(AnalysisJob).filter(
        AnalysisJob.upload_id == done_uid).one().status == "done"
    assert db.query(Trade).filter(Trade.upload_id == done_uid).count() == 1
    assert db.query(AnalysisResult).filter(
        AnalysisResult.upload_id == done_uid).count() == 1
    db.close()


def test_worker_uses_own_session(app_env):
    """worker는 요청 세션이 아니라 SessionLocal로 자체 세션을 연다."""
    before = app_env["session_count"]["n"]
    _upload(app_env["client"])
    assert app_env["session_count"]["n"] > before  # worker가 팩토리에서 새로 열었음


def test_worker_failure_records_reason_internally(app_env, monkeypatch):
    """분석 예외 → failed + error_reason 내부 기록, 폴링 응답에는 미노출."""
    from pipeline import jobs as jobs_mod

    def boom(*a, **k):
        raise RuntimeError("내부 원인: pykrx 죽음")

    monkeypatch.setattr(jobs_mod, "run_pipeline_from_db", boom)
    r = _upload(app_env["client"])
    jid = r.json()["job_id"]

    from orm import AnalysisJob
    db = app_env["Session"]()
    job = db.query(AnalysisJob).filter(AnalysisJob.id == jid).one()
    assert job.status == "failed"
    assert "pykrx" in job.error_reason  # 내부 기록은 상세 유지
    db.close()

    poll = app_env["client"].get(f"/jobs/{jid}")
    assert poll.status_code == 200
    body = poll.json()
    assert body["status"] == "failed"
    assert body["error_type"] == "RuntimeError"  # 클래스명만 노출 (진단용, 2026-09-02)
    assert body.get("message") == "분석에 실패했습니다"
    assert "pykrx" not in str(body)     # 상세 원인 비노출


def test_get_job_polling_contract(app_env):
    """pending/done 응답 형태 + 미존재 404."""
    r = _upload(app_env["client"])
    jid, uid = r.json()["job_id"], r.json()["upload_id"]

    poll = app_env["client"].get(f"/jobs/{jid}")
    assert poll.status_code == 200
    assert poll.json() == {"job_id": jid, "status": "done", "upload_id": uid}

    assert app_env["client"].get("/jobs/99999").status_code == 404


def test_get_job_owner_mismatch_404(app_env):
    """job은 소유자와 다른 로그인 유저로 조회 시 404 (존재 여부도 숨김),
    본인으로 조회 시 200.

    [JWT 도입 후 수정] 예전엔 ?user_id= 쿼리 파라미터로 신원을 흉내냈지만,
    이제 신원은 JWT(여기서는 override된 get_current_user)로만 정해진다.
    그래서 쿼리 파라미터 대신 app_env["current_user_id"]를 바꿔서
    "다른 사람으로 로그인한 상태"를 흉내낸다. 완전 미인증(토큰 없음) 시
    401이 나는 것은 get_current_user 자체의 책임이라 override로 대체된
    이 테스트 스위트에서는 검증하지 않는다 — auth.py 자체 유닛테스트에서
    다뤄야 할 영역.
    """
    from orm import AnalysisJob, CsvUpload, User

    db = app_env["Session"]()
    owner = User(name="주인")
    db.add(owner)
    db.flush()
    up = CsvUpload(file_name="x.csv")
    db.add(up)
    db.flush()
    job = AnalysisJob(upload_id=up.id, user_id=owner.id, status="done")
    db.add(job)
    db.commit()
    jid, oid = job.id, owner.id
    db.close()

    c = app_env["client"]

    app_env["current_user_id"]["id"] = oid + 1
    assert c.get(f"/jobs/{jid}").status_code == 404  # 타인으로 로그인 → 존재 숨김

    app_env["current_user_id"]["id"] = oid
    assert c.get(f"/jobs/{jid}").status_code == 200  # 본인으로 로그인 → 정상 조회