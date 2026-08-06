from sqlalchemy import Column, Integer, String, Date, BigInteger, Float, Boolean, JSON, TIMESTAMP, ForeignKey
from sqlalchemy.sql import func
from database import Base

class User(Base):
    __tablename__ = "users"

    id         = Column(Integer, primary_key=True, index=True)
    name       = Column(String(50), nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())

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
    """업로드 1건당 분석 작업 1개 추적 (2-2 비동기 전환).

    csv_uploads.status(CSV 저장 여부)와 역할이 다름 — 여기의 status는 분석
    진행 상태(pending→running→done|failed)이고 프론트가 폴링으로 읽는 값.
    upload_id unique = 같은 업로드에 job 중복 생성을 DB 제약으로 차단.
    상태 전이는 pipeline.jobs의 조건부 UPDATE로만 수행(역방향 전이 없음)."""
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
    rule_score  = Column(Float)
    stat_score  = Column(Float)
    lstm_score  = Column(Float)
    final_score = Column(Float)
    is_anomaly  = Column(Boolean)
    xai_result  = Column(JSON)
    analyzed_at = Column(TIMESTAMP, server_default=func.now())
