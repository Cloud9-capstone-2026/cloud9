"""
한국투자증권 API 연결 및 현재가 수신
"""
import os
import mojito
from dotenv import load_dotenv

load_dotenv()

def get_broker():
    return mojito.KoreaInvestment(
        api_key=os.getenv("KOREA_INVESTMENT_API_KEY"),
        api_secret=os.getenv("KOREA_INVESTMENT_API_SECRET"),
        acc_no=os.getenv("KOREA_INVESTMENT_ACC_NO"),
        mock=False
    )

def fetch_current_price(broker, symbol: str) -> int:
    response = broker.fetch_price(symbol)
    return int(response['output']['stck_prpr'])

def create_order(*args, **kwargs):
    raise NotImplementedError("실제 주문은 MVP에서 사용하지 않습니다.")