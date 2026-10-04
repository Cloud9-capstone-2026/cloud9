"""
회원 탈퇴 시 계정과 그 계정의 모든 데이터를 즉시 삭제한다.

2026-10-04: 30일 유예기간 정책을 폐지하고 즉시 삭제로 전환(도경과 협의).
유예기간 중에는 로그인이 막히는데 프론트에 복구 경로가 없어 유예기간이
사실상 "데이터 보관 + 같은 이메일 재가입 차단"으로만 작동했고, 복구 UI를
로컬/소셜 두 갈래로 만드는 비용 대비 실익이 적다고 판단. 대신 탈퇴 모달에
"업로드한 거래내역과 분석 결과가 즉시 영구 삭제됩니다" 경고를 둔다.

FK에 ondelete=CASCADE를 걸지 않고 애플리케이션 레벨에서 자식→부모 순서로
직접 삭제한다(기존 FK 제약을 건드리는 마이그레이션을 피하기 위한 의도적
선택, 2026-09-02). 새 테이블에 users/csv_uploads/trades를 가리키는 FK가
생기면 반드시 여기에도 추가할 것 — tests/test_withdrawal_cascade.py가
FK 강제 상태로 검사한다.

호출자가 commit/rollback을 책임진다.
"""
from orm import (AnalysisJob, AnalysisResult, CsvUpload, Notification,
                 RuleChangeLog, SurveyResult, Trade, TradeJournal, UploadFile,
                 User, UserRule)


def delete_user_cascade(db, user_id: int) -> None:
    """FK CASCADE 없이 자식 테이블부터 순서대로 삭제."""
    upload_ids = [
        row.id for row in db.query(CsvUpload.id).filter(CsvUpload.user_id == user_id).all()
    ]

    # 알림(→ users·analysis_jobs·csv_uploads), 거래일지(→ users·trades)는 부모보다
    # 먼저 지운다. 2026-09-10에 두 테이블이 생기면서 여기 추가가 빠져 있었다 —
    # Postgres는 FK를 강제하므로, 알림이 하나라도 있는 계정(업로드한 적 있는
    # 모든 계정)은 삭제가 FK 위반으로 실패하고 배치 전체가 롤백됐다.
    db.query(Notification).filter(Notification.user_id == user_id).delete(synchronize_session=False)
    db.query(TradeJournal).filter(TradeJournal.user_id == user_id).delete(synchronize_session=False)

    if upload_ids:
        db.query(AnalysisResult).filter(AnalysisResult.upload_id.in_(upload_ids)).delete(synchronize_session=False)
        db.query(AnalysisJob).filter(AnalysisJob.upload_id.in_(upload_ids)).delete(synchronize_session=False)
        db.query(UploadFile).filter(UploadFile.upload_id.in_(upload_ids)).delete(synchronize_session=False)
        db.query(Trade).filter(Trade.upload_id.in_(upload_ids)).delete(synchronize_session=False)

    # upload_id로 안 걸리는 잔여분(레거시 직접 저장 등) 정리
    db.query(AnalysisResult).filter(AnalysisResult.user_id == user_id).delete(synchronize_session=False)
    db.query(AnalysisJob).filter(AnalysisJob.user_id == user_id).delete(synchronize_session=False)
    db.query(Trade).filter(Trade.user_id == user_id).delete(synchronize_session=False)

    db.query(CsvUpload).filter(CsvUpload.user_id == user_id).delete(synchronize_session=False)
    db.query(SurveyResult).filter(SurveyResult.user_id == user_id).delete(synchronize_session=False)
    db.query(UserRule).filter(UserRule.user_id == user_id).delete(synchronize_session=False)
    db.query(RuleChangeLog).filter(RuleChangeLog.user_id == user_id).delete(synchronize_session=False)

    db.query(User).filter(User.id == user_id).delete(synchronize_session=False)