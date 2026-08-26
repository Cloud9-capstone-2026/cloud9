"""
AWS Systems Manager Parameter Store에서 진짜 비밀값 3개
(DATABASE_URL / JWT_SECRET_KEY / GMAIL_APP_PASSWORD)를 읽어와 os.environ에
주입한다 (2026-08-26, .env 평문 저장에서 전환).

배경: 이 3개는 EC2 .env에서 완전히 제거했다. 대신 Parameter Store에
`/canary/DATABASE_URL` 등의 이름으로 SecureString으로 저장해두고, EC2에는
이 3개 파라미터만 읽을 수 있는 최소 권한 IAM 역할(canary-ec2-parameter-store-role)을
붙여뒀다. Secrets Manager가 아니라 Parameter Store SecureString을 쓴 이유는
비용(Secrets Manager는 시크릿당 월 $0.40, Parameter Store Standard는 무료)
— 이 프로젝트 규모엔 자동 로테이션 같은 Secrets Manager 전용 기능이 필요
없어서 오버스펙이라고 판단함(2026-08-26 결정).

인증 방식: boto3가 EC2에 붙은 IAM 역할을 자동으로 인식한다(인스턴스
메타데이터 서비스 경유) — 액세스키를 코드나 .env에 별도로 넣지 않는다.

로컬 개발 환경 폴백: 나림 로컬 PC에는 이 IAM 역할이 없으므로 boto3 호출이
실패한다(NoCredentialsError 등). 이건 정상 상황이므로 조용히 무시하고
넘어가며, 이 경우 .env에 남아있는 값(로컬 개발용)을 그대로 쓰게 된다 —
즉 로컬 .env는 지금처럼 계속 3개 값을 다 갖고 있어야 한다. EC2 .env에서만
이 3개를 지운 상태다.

주의(트레이드오프): EC2에서 이 호출이 실패하면(IAM 역할 설정 오류, 파라미터
이름 오타 등) 앱은 죽지 않고 .env의 값(EC2는 이미 지운 상태라 비어있음)으로
넘어가 database.py 등이 기본값(sqlite)으로 조용히 폴백할 수 있다 — 즉
"운영에서 로컬 SQLite로 조용히 전환되는" 실패 모드가 이론적으로 가능하다.
그래서 실패 시 반드시 눈에 띄는 ERROR 로그를 남긴다(journalctl -u canary로
확인 가능) — email_service.py가 발송 실패를 조용히 삼키는 것과 같은 설계
철학이지만, 로그 레벨만 WARNING이 아닌 ERROR로 더 강하게 남긴다(DB 연결
정보라 잘못되면 email보다 훨씬 치명적이라서).
"""
import logging
import os

logger = logging.getLogger("canary.secrets")

_PARAMETER_STORE_PREFIX = "/canary/"
_MANAGED_KEYS = ("DATABASE_URL", "JWT_SECRET_KEY", "GMAIL_APP_PASSWORD")


def load_secrets_into_env(region_name: str = "ap-northeast-2") -> None:
    """Parameter Store에서 값을 가져와 os.environ에 덮어쓴다.

    EC2에서 성공하면: os.environ이 Parameter Store 값으로 갱신됨(운영 진실).
    로컬에서 실패하면: 아무 것도 안 바뀜(.env 값 그대로 유지) — 조용히 리턴.
    """
    try:
        import boto3
        from botocore.exceptions import BotoCoreError, ClientError
    except ImportError:
        # boto3 자체가 설치 안 된 환경(있을 수 없지만 방어적으로) — 조용히 스킵
        return

    names = [f"{_PARAMETER_STORE_PREFIX}{key}" for key in _MANAGED_KEYS]

    try:
        client = boto3.client("ssm", region_name=region_name)
        response = client.get_parameters(Names=names, WithDecryption=True)
    except (BotoCoreError, ClientError):
        # 로컬 개발 환경(IAM 역할 없음)에서는 여기로 항상 빠짐 — 정상.
        # EC2에서 이 경로를 타면(자격증명은 있는데 호출 자체가 실패) 심각한
        # 문제이므로 debug가 아닌 warning으로 남긴다.
        logger.warning(
            "Parameter Store 접근 실패 — 로컬 개발 환경이면 정상(.env로 폴백). "
            "EC2라면 IAM 역할/리전 설정을 확인할 것.", exc_info=True,
        )
        return
    except Exception:
        logger.warning("Parameter Store 호출 중 예상 못한 오류", exc_info=True)
        return

    fetched = {
        p["Name"][len(_PARAMETER_STORE_PREFIX):]: p["Value"]
        for p in response.get("Parameters", [])
    }
    invalid = response.get("InvalidParameters", [])
    if invalid:
        logger.error(
            "Parameter Store에서 찾을 수 없는 파라미터: %s — "
            "이름 오타 또는 아직 생성 안 됨. 해당 값은 .env/기본값으로 폴백됨.",
            invalid,
        )

    if not fetched:
        return

    for key, value in fetched.items():
        os.environ[key] = value

    logger.info("Parameter Store에서 비밀값 %d개 로드 완료: %s",
                len(fetched), ", ".join(sorted(fetched.keys())))


def get_secret(key: str, region_name: str = "ap-northeast-2") -> str | None:
    """단일 값 조회(예: reset_db.py --prod). 실패 시 None.

    load_secrets_into_env()와 별개 함수를 둔 이유: reset_db.py는 FastAPI 앱
    부팅 경로가 아니라 사람이 직접 실행하는 1회성 유틸이라, 굳이 os.environ
    전체를 건드리지 않고 값 하나만 받아서 쓰는 게 더 명확하다.
    """
    try:
        import boto3
        from botocore.exceptions import BotoCoreError, ClientError
    except ImportError:
        return None

    if key not in _MANAGED_KEYS:
        raise ValueError(f"Parameter Store 관리 대상이 아닌 키입니다: {key}")

    try:
        client = boto3.client("ssm", region_name=region_name)
        response = client.get_parameter(
            Name=f"{_PARAMETER_STORE_PREFIX}{key}", WithDecryption=True,
        )
        return response["Parameter"]["Value"]
    except (BotoCoreError, ClientError):
        return None