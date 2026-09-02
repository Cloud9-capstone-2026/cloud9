"""
업로드 원본 파일 보관 — upload_files 테이블(orm.UploadFile).

원본을 보관하는 이유: 매핑·분석은 백그라운드에서 나중에 돌므로 업로드 시점의
파일이 남아 있어야 하고, 실패 시 원인 확인·재시도의 재료가 된다.

orm.UploadFile(upload_id FK unique, content bytea, size, created_at)에 저장·조회.
파일명은 csv_uploads.file_name을 재사용(중복 저장 안 함).
디스크 폴백(backend/uploads/)은 테이블이 생기기 전의 임시 다리였고 2026-09-02 삭제 —
그 이전에 디스크에만 저장된 옛 업로드는 더 이상 코드로 읽히지 않는다(파일은 존치).
"""

from orm import CsvUpload, UploadFile

ALLOWED_EXTS = (".csv", ".xlsx", ".xls")  # 업로드 라우터의 확장자 검사용


def save_upload(upload_id: int, raw: bytes, db) -> None:
    """원본을 upload_files 행으로 저장 (commit은 호출자가)."""
    db.add(UploadFile(upload_id=upload_id, content=raw, size=len(raw)))


def load_upload(upload_id: int, db) -> tuple[bytes, str] | None:
    """원본 (bytes, 파일명). 행이 없으면 None — 호출자가 실패 처리."""
    row = db.query(UploadFile).filter(UploadFile.upload_id == upload_id).first()
    if row is None:
        return None
    up = db.query(CsvUpload).filter(CsvUpload.id == upload_id).first()
    return bytes(row.content), (up.file_name if up else f"{upload_id}")
