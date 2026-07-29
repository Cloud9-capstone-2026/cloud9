"""
출력 스키마 정의. 지난번 확정한 표와 1:1 대응.
"""
 
from dataclasses import dataclass, field
 
from .. import config
 
 
@dataclass
class Trade:
    거래일자: object
    agent_id: str
    종목코드: str
    거래구분: str  # "매수" | "매도"
    거래수량: int
    거래단가: float
    # "HH:MM:SS". agent가 장중(09:00~15:30)에서 독립 샘플링해 전달, 가격과 무관.
    # 주의: 분포용 참고 필드일 뿐 "하루 안의 매매 순서" 신호가 아니다. agent 실행 순서는
    # model.step()의 shuffle_do로 매일 무작위라, 처리시간으로 체결 순서를 재구성하면 안 된다.
    처리시간: str
    거래금액: float = field(init=False)
    수수료: float = field(init=False)
    거래세: float = field(init=False)
    정산금액: float = field(init=False)
    # 체결 후 현금 잔고 스냅샷 — Trade 생성 뒤 agent가 시뮬레이션 상태를 반영해 채움.
    예수금: float = field(init=False, default=0.0)  # 거래 후 현금 잔고(원)
    편향라벨: dict = field(default_factory=dict)
 
    def __post_init__(self):
        self.거래금액 = self.거래수량 * self.거래단가
        self.수수료 = round(self.거래금액 * config.FEE_RATE)
        self.거래세 = (
            round(self.거래금액 * config.TAX_RATE) if self.거래구분 == "매도" else 0
        )
        if self.거래구분 == "매수":
            self.정산금액 = self.거래금액 + self.수수료
        else:
            self.정산금액 = self.거래금액 - self.수수료 - self.거래세
 
    def to_dict(self) -> dict:
        return {
            "거래일자": self.거래일자,
            "agent_id": self.agent_id,
            "종목코드": self.종목코드,
            "거래구분": self.거래구분,
            "거래수량": self.거래수량,
            "거래단가": self.거래단가,
            "거래금액": self.거래금액,
            "수수료": self.수수료,
            "거래세": self.거래세,
            "정산금액": self.정산금액,
            "예수금": self.예수금,
            "처리시간": self.처리시간,
            "편향라벨": self.편향라벨,
        }
 