from sqlalchemy import Column, Integer, String, Date, BigInteger, Float, Boolean, JSON, TIMESTAMP
from sqlalchemy.sql import func
from database import Base

class User(Base):
    __tablename__ = "users"

    id         = Column(Integer, primary_key=True, index=True)
    name       = Column(String(50), nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())

class Trade(Base):
    __tablename__ = "trades"

    id       = Column(Integer, primary_key=True, index=True)
    user_id  = Column(Integer, nullable=True)
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

class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id          = Column(Integer, primary_key=True, index=True)
    user_id     = Column(Integer, nullable=True)
    rule_score  = Column(Float)
    stat_score  = Column(Float)
    lstm_score  = Column(Float)
    final_score = Column(Float)
    is_anomaly  = Column(Boolean)
    xai_result  = Column(JSON)
    analyzed_at = Column(TIMESTAMP, server_default=func.now())