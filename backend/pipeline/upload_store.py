"""
업로드 원본 파일 보관 — DB(upload_files 테이블) 우선, 테이블이 아직 없으면 디스크.

원본을 보관하는 이유: 매핑·분석은 백그라운드에서 나중에 돌므로 업로드 시점의
파일이 남아 있어야 하고, 실패 시 원인 확인·재시도의 재료가 된다.

DB 경로: orm.UploadFile(upload_id FK unique, content bytea, size, created_at — 노션
"스키마 업데이트 내용" 초안)이 정의돼 있고 세션이 주어지면 그 테이블에 저장·조회한다.
파일명은 csv_uploads.file_name을 재사용(중복 저장 안 함). 테이블 생성은 팀장 영역이라
orm.py는 여기서 건드리지 않고 getattr로 있는지만 본다 — user_rules 로더와 같은 방식.

디스크 경로: backend/uploads/{upload_id}.{확장자}. ponytail: 테이블이 생기기 전까지
서버 업로드가 깨지지 않게 두는 임시 다리 — orm.UploadFile이 main에 들어오면
save/load의 디스크 분기와 UPLOAD_DIR·find_upload를 삭제할 것(PROCESS 미결 항목).
"""

from pathlib import Path

UPLOAD_DIR = Path(__file__).resolve().parents[1] / "uploads"
ALLOWED_EXTS = (".csv", ".xlsx", ".xls")


def _model():
    """orm.UploadFile — 팀장이 테이블을 추가하면 자동으로 DB 경로가 켜진다."""
    try:
        import orm
        return getattr(orm, "UploadFile", None)
    except Exception:  # noqa: BLE001 — orm 자체를 못 읽는 환경(단위 테스트)이면 디스크
        return None


def save_upload(upload_id: int, filename: str, raw: bytes, db=None) -> None:
    """원본 저장. db가 있고 테이블이 있으면 DB 행(호출자가 commit), 아니면 디스크."""
    model = _model()
    if db is not None and model is not None:
        db.add(model(upload_id=upload_id, content=raw, size=len(raw)))
        return
    ext = Path(filename or "").suffix.lower()
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    (UPLOAD_DIR / f"{upload_id}{ext}").write_bytes(raw)


def load_upload(upload_id: int, db=None) -> tuple[bytes, str] | None:
    """원본 (bytes, 파일명). DB 행 → csv_uploads.file_name과 함께, 없으면 디스크, 둘 다 없으면 None."""
    model = _model()
    if db is not None and model is not None:
        row = db.query(model).filter(model.upload_id == upload_id).first()
        if row is not None:
            from orm import CsvUpload
            up = db.query(CsvUpload).filter(CsvUpload.id == upload_id).first()
            return bytes(row.content), (up.file_name if up else f"{upload_id}")
    path = find_upload(upload_id)
    if path is None:
        return None
    return path.read_bytes(), path.name


def find_upload(upload_id: int) -> Path | None:
    """디스크 경로 조회(옛 인터페이스 — 테이블 도입 후 삭제 대상)."""
    for ext in ALLOWED_EXTS:
        path = UPLOAD_DIR / f"{upload_id}{ext}"
        if path.exists():
            return path
    return None
