"""
reset_db.py — 데모 전 DB 초기화 유틸.

trades / csv_uploads / analysis_results 테이블을 비우고 id를 1부터 재시작한다.
새 분석 로직은 "이전 업로드(upload_id < 현재)"를 baseline으로 보므로,
연습으로 쌓인 데이터가 남아 있으면 안 됨 → 데모 직전 1회 실행.

실행: backend 디렉토리에서  python reset_db.py
"""

from sqlalchemy import text
from database import engine, DATABASE_URL

TABLES = "analysis_results, trades, csv_uploads"


def main():
    host = DATABASE_URL.split("@")[-1]  # 비밀번호 제외, 호스트만 표시
    print(f"연결 대상 DB: {host}")
    ans = input(f"[{TABLES}] 테이블을 모두 비웁니다. 진행할까요? (yes 입력): ")
    if ans.strip().lower() != "yes":
        print("취소됨.")
        return

    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE TABLE {TABLES} RESTART IDENTITY CASCADE;"))
    print("초기화 완료 — id가 1부터 재시작됩니다.")


if __name__ == "__main__":
    main()
