"""회원 탈퇴 유예 처리 + CSV 원본 90일 보관 정책 구현
- users: deleted_at, scheduled_deletion_at 추가 (탈퇴 요청 시각 / 실제 삭제 예정 시각)
- upload_files.content, size: nullable로 변경 (90일 경과 시 원본만 비우기 위함)

Revision ID: a2b3c4d5e6f7
Revises: f6a7b8c9d0e1
Create Date: 2026-09-02
"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = 'a2b3c4d5e6f7'
down_revision: Union[str, Sequence[str], None] = 'd4f7a2b9c5e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('deleted_at', sa.TIMESTAMP(timezone=True), nullable=True))
    op.add_column('users', sa.Column('scheduled_deletion_at', sa.TIMESTAMP(timezone=True), nullable=True))
    op.alter_column('upload_files', 'content', nullable=True)
    op.alter_column('upload_files', 'size', nullable=True)


def downgrade() -> None:
    op.alter_column('upload_files', 'size', nullable=False)
    op.alter_column('upload_files', 'content', nullable=False)
    op.drop_column('users', 'scheduled_deletion_at')
    op.drop_column('users', 'deleted_at')