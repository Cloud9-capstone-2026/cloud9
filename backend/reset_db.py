"""
reset_db.py — DB 초기화 유틸.

trades / csv_uploads / analysis_results 테이블을 비우고 id를 1부터 재시작한다.
새 분석 로직은 "이전 업로드(upload_id < 현재)"를 baseline으로 보므로,
연습으로 쌓인 데이터가 남아 있으면 안 됨 → 데모 직전 1회 실행.

실행 (backend 디렉토리에서):
  python reset_db.py            # 로컬 DB 초기화 (database.py 기본값 = SQLite local.db)
  python reset_db.py --prod     # 운영 DB 초기화 (backend/.env 의 DATABASE_URL 사용)

--prod 는 backend/.env 에 운영 DB 주소가 있어야 동작한다 (.env 는 git 에 올라가지 않음):
  DATABASE_URL=postgresql://...@...railway
"""

import sys
from pathlib import Path

from sqlalchemy import create_engine, text, inspect

TABLES = ["analysis_results", "trades", "csv_uploads"]


def _load_prod_url() -> str:
    """backend/.env 에서 DATABASE_URL(운영 주소)을 읽는다."""
    env_path = Path(__file__).resolve().parent / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("DATABASE_URL="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    print("운영 DB 주소를 찾을 수 없습니다. backend/.env 에 DATABASE_URL=... 를 넣어주세요.")
    sys.exit(1)


def main():
    is_prod = "--prod" in sys.argv
    if is_prod:
        url = _load_prod_url()
    else:
        from database import DATABASE_URL  # env 없으면 기본 SQLite
        url = DATABASE_URL

    host = url.split("@")[-1] if "@" in url else url  # 비밀번호 제외, 호스트만 표시
    label = "운영(PROD)" if is_prod else "로컬"
    print(f"[{label}] 연결 대상 DB: {host}")

    ans = input(f"{TABLES} 테이블을 모두 비웁니다. 진행할까요? (yes 입력): ")
    if ans.strip().lower() != "yes":
        print("취소됨.")
        return

    engine = create_engine(url)
    existing = set(inspect(engine).get_table_names())

    with engine.begin() as conn:
        if engine.dialect.name == "sqlite":
            # SQLite 는 TRUNCATE 미지원 → DELETE + sqlite_sequence 초기화
            for t in TABLES:
                if t in existing:
                    conn.execute(text(f"DELETE FROM {t}"))
            if "sqlite_sequence" in existing:
                conn.execute(text(
                    "DELETE FROM sqlite_sequence "
                    "WHERE name IN ('analysis_results', 'trades', 'csv_uploads')"
                ))
        else:
            conn.execute(text(
                "TRUNCATE TABLE analysis_results, trades, csv_uploads RESTART IDENTITY CASCADE"
            ))

    print("초기화 완료 — id가 1부터 재시작됩니다.")


if __name__ == "__main__":
    main()
