"""
이메일 발송 (Gmail SMTP).

[2026-08-18] Gmail 앱 비밀번호 방식으로 확정. AWS SES는 배제 — 샌드박스
모드에서는 발신·수신 이메일 둘 다 사전 인증이 필요해, 회원가입 즉시
임의 이메일로 보내야 하는 이 서비스 구조상 프로덕션 액세스 승인 전까지는
쓸 수 없음(캡스톤 일정상 배제).

발신 계정은 나림 개인 Gmail이 아니라 팀 전용 계정(예: canary.noreply@gmail.com)
을 새로 만들어 쓸 것 — 개인 계정에 앱 비밀번호를 걸면 그 계정 전체가
서버 보안과 얽히고, 발신자 주소도 개인 이메일로 노출된다.

환경변수 (.env에 추가 필요):
  GMAIL_USER          - 발송용 Gmail 주소 (팀 전용 계정)
  GMAIL_APP_PASSWORD  - 위 계정의 앱 비밀번호(16자리, 공백 제거해서 저장).
                         발급 경로: 해당 Gmail 계정에서 2단계 인증을 먼저
                         켠 다음 "앱 비밀번호" 메뉴에서 생성. 2단계 인증이
                         꺼져 있으면 이 메뉴 자체가 안 보인다.

두 값이 비어있으면(로컬 개발 중 아직 .env를 안 채웠을 때) 실제 발송 대신
경고 로그로 대체한다 — 조용히 아무 일도 안 일어나면 "왜 메일이 안 오지"
하고 헤매게 되므로, 눈에 띄게 warning으로 남긴다.

인증 링크의 verify_link는 아직 임시 플레이스홀더. React Native 앱의 실제
딥링크 스킴(예: canary://verify-email?token=...)이 정해지면 교체해야 함 —
도경과 협의 필요.
"""
import logging
import os
import smtplib
from email.mime.text import MIMEText

logger = logging.getLogger("canary.email")

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587


def send_verification_email(to_email: str, token: str) -> None:
    verify_link = f"https://api.canary.example/auth/verify-email?token={token}"

    gmail_user = os.getenv("GMAIL_USER")
    gmail_password = os.getenv("GMAIL_APP_PASSWORD")
    if gmail_password:
        # Google이 화면에 "abcd efgh ijkl mnop"처럼 공백 포함해서 보여주는데,
        # .env에 그대로 붙여넣든 공백 없이 넣든 둘 다 동작하게 여기서 제거.
        gmail_password = gmail_password.replace(" ", "")

    if not gmail_user or not gmail_password:
        logger.warning(
            "GMAIL_USER/GMAIL_APP_PASSWORD 미설정 — 실제 발송 대신 로그로 대체. "
            "[DEV-STUB] %s 앞 인증 링크: %s", to_email, verify_link,
        )
        return

    msg = MIMEText(
        "Canary 이메일 인증을 완료해주세요.\n\n"
        f"아래 링크를 눌러 인증을 마쳐주세요:\n{verify_link}\n\n"
        "이 링크는 24시간 동안 유효합니다.",
        "plain", "utf-8",
    )
    msg["Subject"] = "[Canary] 이메일 인증을 완료해주세요"
    msg["From"] = gmail_user
    msg["To"] = to_email

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.starttls()
            server.login(gmail_user, gmail_password)
            server.sendmail(gmail_user, [to_email], msg.as_string())
        logger.info("인증 메일 발송 성공: %s", to_email)
    except (smtplib.SMTPException, OSError):
        # smtplib.SMTPException 외에, 연결 타임아웃/거부 같은 네트워크 레벨
        # 오류는 OSError 계열이라 별도로 잡아야 함(안 그러면 EC2 보안그룹이
        # 587번 포트를 막고 있을 때 이 예외가 안 잡혀서 회원가입 요청 자체가
        # 500으로 죽는 사고로 이어짐). 메일 서버 일시 장애로 회원가입 자체가
        # 실패하면 안 되므로 로그로만 남기고 삼킨다.
        logger.exception("인증 메일 발송 실패: %s", to_email)