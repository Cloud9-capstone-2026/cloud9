from sqlalchemy import Column, Integer, String, Date, BigInteger, Float, Boolean, JSON, TIMESTAMP, ForeignKey, UniqueConstraint, LargeBinary
from sqlalchemy.sql import func
from database import Base

class User(Base):
    __tablename__ = "users"

    id              = Column(Integer, primary_key=True, index=True)
    name            = Column(String(50), nullable=False)
    email           = Column(String(255), unique=True, nullable=True)   # 추가
    hashed_password = Column(String(255), nullable=True)                 # 추가
    # 소셜로그인/이메일인증 대비 (2026-08-18, 옵션A: 컬럼 확장 방식).
    # provider: 'local' | 'google' | 'kakao' | 'naver'. 계정당 로그인수단 1개 고정.
    provider        = Column(String(20), nullable=True)
    provider_id     = Column(String(255), nullable=True)
    email_verified  = Column(Boolean, nullable=False, default=False)
    # 이메일 인증 6자리 코드 (2026-08-24, 딥링크 방식에서 전환).
    # 원문 코드는 저장하지 않고 HMAC 해시만 저장한다. 재발송 시 이 두 값을
    # 덮어써서 이전 코드를 자동 무효화한다(별도 "무효화" 로직 불필요).
    verification_code_hash       = Column(String(64), nullable=True)
    verification_code_expires_at = Column(TIMESTAMP, nullable=True)
    # 이용약관/개인정보처리방침 동의 (2026-08-26, 도경과 협의 — 회원가입 필드에 추가).
    # 회원가입 시점에 True로 고정 기록. 나중에 약관이 개정되면 재동의 로직이
    # 필요할 수 있는데, 그건 별도 버전 관리(예: agreed_terms_version)가
    # 필요한 영역이라 지금 범위에는 포함하지 않음.
    agreed_terms    = Column(Boolean, nullable=False, default=False)
    agreed_terms_at = Column(TIMESTAMP, nullable=True)
    # 비밀번호 재설정 6자리 코드 (2026-08-27). verification_code_hash와 별도
    # 컬럼으로 둔 이유는 auth.py 주석 참고 — 이메일 인증 코드와 섞이면
    # 서로 덮어쓰는 사고가 날 수 있음.
    password_reset_code_hash       = Column(String(64), nullable=True)
    password_reset_code_expires_at = Column(TIMESTAMP, nullable=True)
    created_at      = Column(TIMESTAMP, server_default=func.now())

    __table_args__ = (
        UniqueConstraint('provider', 'provider_id', name='uq_users_provider_provider_id'),
    )

class CsvUpload(Base):
    __tablename__ = "csv_uploads"

    id          = Column(Integer, primary_key=True, index=True)
    user_id     = Column(Integer, ForeignKey("users.id"), nullable=True)
    file_name   = Column(String(255), nullable=False)
    row_count   = Column(Integer, nullable=True)
    status      = Column(String(20), default="pending")
    uploaded_at = Column(TIMESTAMP, server_default=func.now())

class Trade(Base):
    __tablename__ = "trades"

    id       = Column(Integer, primary_key=True, index=True)
    user_id  = Column(Integer, nullable=True)
    upload_id = Column(Integer, ForeignKey("csv_uploads.id"), nullable=True)
    거래일자 = Column(Date, nullable=False)
    종목명   = Column(String(50), nullable=False)
    거래구분 = Column(String(10), nullable=False)
    거래수량 = Column(Integer, nullable=False)
    거래단가 = Column(Integer, nullable=False)
    거래금액 = Column(BigInteger, nullable=False)
    수수료   = Column(Integer, nullable=False)
    거래세   = Column(Integer, nullable=False)
    정산금액 = Column(BigInteger, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())

class AnalysisJob(Base):
    """업로드 1건당 분석 작업 1개 추적.

    csv_uploads.status(CSV 저장 여부)와 역할이 다름 — 여기의 status는 분석
    진행 상태(pending→running→done|failed)이고 프론트가 폴링으로 읽는 값.
    upload_id unique = 같은 업로드에 job 중복 생성을 DB 제약으로 차단.
    상태 전이는 pipeline.jobs의 조건부 UPDATE로만 수행 가능."""
    __tablename__ = "analysis_jobs"

    id           = Column(Integer, primary_key=True, index=True)
    upload_id    = Column(Integer, ForeignKey("csv_uploads.id"), unique=True, nullable=False)
    user_id      = Column(Integer, ForeignKey("users.id"), nullable=True)
    status       = Column(String(20), nullable=False, default="pending")
    error_reason = Column(String(500), nullable=True)   # 내부 기록용 — API 응답에 미노출
    retry_count  = Column(Integer, nullable=False, default=0)
    created_at   = Column(TIMESTAMP, server_default=func.now())
    started_at   = Column(TIMESTAMP, nullable=True)
    finished_at  = Column(TIMESTAMP, nullable=True)

class UserRule(Base):
    """1계층(Rule-based) 사용자 정의 규칙 파라미터.

    2026-08-07 회의 결정: 1계층을 "사용자가 스스로 정한 절제 규칙" 방식으로
    전환하면서 도입. 스키마는 은우가 pipeline/user_rules.py에 이미 문서화해둔
    "기대 스키마"를 그대로 따른다 — 이 모델이 orm에 실제로 생기는 순간
    pipeline/user_rules.py의 getattr 폴백(orm.UserRule 없으면 기본 조합 사용)이
    자동으로 DB 조회 경로로 전환된다. 즉 이 모델 추가 외에 다른 코드 변경 불필요.

    rule_id 유효값 7종(models/rule_based/templates.py의 TEMPLATES 키와 동기화
    필요): daily_frequency, same_day_roundtrip, min_holding,
    reentry_after_loss, averaging_down, single_buy_cap, daily_total_cap.
    DB 레벨 CHECK 제약은 걸지 않음 — C파트가 템플릿을 추가/변경할 때마다
    스키마 마이그레이션이 필요해지는 결합을 피하기 위함(값 검증은
    pipeline/user_rules.py가 TEMPLATES 조회 실패 시 경고 후 스킵하는 방식으로
    이미 방어하고 있음).

    (user_id, rule_id) unique — 사용자당 규칙 1행, 수정은 UPDATE로(재등록 아님).
    수정은 소급 없이 다음 업로드 분석부터 적용(과거 분석 결과 재계산 안 함)."""
    __tablename__ = "user_rules"
    __table_args__ = (
        UniqueConstraint('user_id', 'rule_id', name='uq_user_rules_user_id_rule_id'),
    )

    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False)
    rule_id    = Column(String(30), nullable=False)
    param      = Column(Float, nullable=True)  # 왕복매매처럼 파라미터 없는 규칙은 null
    enabled    = Column(Boolean, nullable=False, default=True)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())


class UploadFile(Base):
    """업로드 CSV/XLS 원본 파일 실제 바이트를 DB에 보관.

    배경: 기존엔 EC2 디스크(backend/uploads/)에만 저장돼 있어 서버 교체 시
    유실 위험이 있었고, 개인 거래내역이라는 데이터 성격상 디스크에 평문
    파일로 흩어져 있는 것도 보안 정책상 부적절 → DB로 이관.

    csv_uploads에 컬럼으로 안 붙이고 별도 테이블로 분리한 이유: GET
    /trades/uploads(업로드 목록 조회)가 csv_uploads를 통째로 조회하는데,
    content(최대 10MB)가 같은 행에 있으면 목록 조회 한 번에 수십MB를
    끌어오게 된다. 분리해두면 목록 조회는 가볍고, 원본 파일은 실제로
    분석(map_file)에 쓰일 때만 이 테이블을 별도로 읽는다.

    파일명은 여기 저장 안 함 — csv_uploads.file_name에 이미 있어 중복
    저장을 피함(pipeline/upload_store.load_upload가 두 테이블을 조합해
    (bytes, filename) 튜플로 반환).

    이 모델이 orm에 생기는 순간 pipeline/upload_store.py의 getattr 폴백이
    자동으로 DB 저장/조회 경로로 전환된다(디스크 저장 코드는 폴백용으로
    남아있으나, 이후 backend/uploads/ 폴더 배포 시 유지 관리는 불필요해짐 —
    당장 그 코드를 지우는 건 별도 후속 작업으로 남겨둠).

    보관 정책(문서화, 이번 커밋에는 로직 미구현 — 별도 배치 작업 필요):
    1) 회원 탈퇴 시 즉시 삭제(upload_files + csv_uploads/trades 연쇄 삭제 포함)
    2) 업로드 후 90일 지난 원본은 분석 결과는 유지하고 원본 파일만 삭제
    두 정책 모두 아직 구현 안 됨 — 탈퇴 기능 자체가 없고, 90일 정리 배치도
    별도 스케줄러가 필요한 작업이라 이번 스키마 추가 범위 밖."""
    __tablename__ = "upload_files"

    id         = Column(Integer, primary_key=True, index=True)
    upload_id  = Column(Integer, ForeignKey("csv_uploads.id"), unique=True, nullable=False)
    content    = Column(LargeBinary, nullable=False)
    size       = Column(Integer, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())


class SurveyResult(Base):
    """투자 성향 자가진단(20문항) 결과 1회 제출분.

    스펙(2026-08-17 확정): 축당 5문항 4축(disposition_strength/overconfidence/
    lottery_preference/herd_sensitivity), 1~5 리커트, 일부 문항 reverse 채점
    (6-응답값). raw(5~25)를 (raw-5)/20*100으로 0~100 정규화, 50 이상 high.
    type_code는 4축을 이 순서로 이어붙인 H/L 4글자.

    answers는 원본 응답(reverse 적용 전)을 감사·재계산 대비용으로 JSONB에
    같이 저장 — 나중에 reverse 채점 대상 문항이 바뀌어도 과거 응답으로
    재계산 가능하게 하기 위함 (xai_result를 JSONB로 남기는 것과 같은 이유)."""
    __tablename__ = "survey_results"

    id      = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    disposition_strength_raw        = Column(Integer, nullable=False)
    disposition_strength_normalized = Column(Float, nullable=False)
    disposition_strength_level      = Column(String(4), nullable=False)  # 'high' | 'low'

    overconfidence_raw        = Column(Integer, nullable=False)
    overconfidence_normalized = Column(Float, nullable=False)
    overconfidence_level      = Column(String(4), nullable=False)

    lottery_preference_raw        = Column(Integer, nullable=False)
    lottery_preference_normalized = Column(Float, nullable=False)
    lottery_preference_level      = Column(String(4), nullable=False)

    herd_sensitivity_raw        = Column(Integer, nullable=False)
    herd_sensitivity_normalized = Column(Float, nullable=False)
    herd_sensitivity_level      = Column(String(4), nullable=False)

    type_code = Column(String(4), nullable=False)  # 예: 'HLHL'
    answers   = Column(JSON, nullable=False)        # [{question_id, value}, ...] 원본 응답

    created_at = Column(TIMESTAMP, server_default=func.now())


class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id          = Column(Integer, primary_key=True, index=True)
    user_id     = Column(Integer, nullable=True)
    upload_id   = Column(Integer, ForeignKey("csv_uploads.id"), nullable=True)
    # 재시도(retry_count) 시 "몇 번째 시도의 결과인지" 구분용. upload_id만으로는
    # 같은 업로드에 재시도가 여러 번 있었을 때 결과가 뒤섞임. nullable=True인 이유:
    # routers/analysis.py의 POST(레거시 직접 저장 경로)는 job 문맥이 없어 None으로 남음.
    job_id      = Column(Integer, ForeignKey("analysis_jobs.id"), nullable=True)
    rule_score  = Column(Float)
    stat_score  = Column(Float)
    lstm_score  = Column(Float)
    final_score = Column(Float)
    is_anomaly  = Column(Boolean)
    xai_result  = Column(JSON)
    analyzed_at = Column(TIMESTAMP, server_default=func.now())