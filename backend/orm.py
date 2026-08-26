from sqlalchemy import Column, Integer, String, Date, BigInteger, Float, Boolean, JSON, TIMESTAMP, ForeignKey, UniqueConstraint
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