"""
레이트리밋 공용 limiter 인스턴스.

main.py(예외 핸들러 등록용)와 routers/auth.py(데코레이터 사용) 양쪽에서
같은 limiter를 참조해야 하는데, main.py가 routers를 import하고 routers가
다시 main.py의 뭔가를 import하면 순환 참조가 생긴다. 그래서 limiter
인스턴스 자체를 이 독립 모듈에 두고 양쪽에서 여기서 import한다.

key_func=get_remote_address: 클라이언트 IP 기준으로 카운트.
(EC2 뒤에 로드밸런서/프록시가 붙으면 실제 클라이언트 IP 대신 프록시 IP만
잡힐 수 있음 — 그때는 X-Forwarded-For 헤더를 보는 key_func으로 바꿔야 함.
지금 구조(EC2 단일 인스턴스, 프록시 없음)에서는 문제없음.)
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)