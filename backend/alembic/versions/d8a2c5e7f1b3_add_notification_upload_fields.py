"""add file_name/trade_count to notifications

프론트 NotifRaw 타입(kind: analysis/analyzeFail/upload/uploadFail, file,
count?, time) 계약에 맞추기 위해 컬럼 2개 추가. type 값 자체(analysis_done→
analysis 등)는 앱 코드에서만 바뀌는 부분이라 스키마 변경 불필요.

Revision ID: d8a2c5e7f1b3
Revises: c3f9a1b2d4e6
Create Date: 2026-09-09
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'd8a2c5e7f1b3'
down_revision: Union[str, Sequence[str], None] = 'c3f9a1b2d4e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('notifications', sa.Column('file_name', sa.String(length=255), nullable=True))
    op.add_column('notifications', sa.Column('trade_count', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('notifications', 'trade_count')
    op.drop_column('notifications', 'file_name')