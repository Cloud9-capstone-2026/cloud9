"""
업로드 원본 파일 보관 — 현재는 디스크(backend/uploads/), DB 이관은 추후(팀장 협의).

원본을 보관하는 이유: 매핑·분석은 백그라운드에서 나중에 돌므로 업로드 시점의
파일이 남아 있어야 하고, 실패 시 원인 확인·재시도의 재료가 된다.
파일명은 {upload_id}.{확장자} — DB의 csv_uploads 행과 1:1.
"""

from pathlib import Path

UPLOAD_DIR = Path(__file__).resolve().parents[1] / "uploads"
ALLOWED_EXTS = (".csv", ".xlsx", ".xls")


def save_upload(upload_id: int, filename: str, raw: bytes) -> Path:
    ext = Path(filename or "").suffix.lower()
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    path = UPLOAD_DIR / f"{upload_id}{ext}"
    path.write_bytes(raw)
    return path


def find_upload(upload_id: int) -> Path | None:
    for ext in ALLOWED_EXTS:
        path = UPLOAD_DIR / f"{upload_id}{ext}"
        if path.exists():
            return path
    return None
