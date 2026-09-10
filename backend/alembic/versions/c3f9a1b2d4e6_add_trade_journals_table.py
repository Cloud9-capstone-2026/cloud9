"""add trade_journals table

거래 1건당 사용자가 직접 쓰는 매매 일지 1건(1:1). 프론트 스펙(2026-09,
JournalWriteScreen.tsx) 반영 — 실제 입력 필드는 emotion/reason/review 3개뿐,
stock/date/type/memo/risk는 저장 안 하고 조회 시 파생(라우터에서 처리).

Revision ID: c3f9a1b2d4e6
Revises: b7c1d4e8f2a9
Create Date: 2026-09-09
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'c3f9a1b2d4e6'
down_revision: Union[str, Sequence[str], None] = 'b7c1d4e8f2a9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'trade_journals',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('trade_id', sa.Integer(), sa.ForeignKey('trades.id'), nullable=False),
        sa.Column('emotion', sa.String(length=20), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('review', sa.Text(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint('user_id', 'trade_id', name='uq_trade_journals_user_id_trade_id'),
    )
    op.create_index('ix_trade_journals_user_id', 'trade_journals', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_trade_journals_user_id', table_name='trade_journals')
    op.drop_table('trade_journals')