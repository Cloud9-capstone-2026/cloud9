"""analysis_results에 trade_id 추가 — 거래 1건과 분석 결과 1행의 1:1 연결 키

기존에는 upload_id + (날짜, 종목명)으로만 연결할 수 있어, 분할 체결처럼 내용이
동일한 거래 여러 건은 어느 결과가 어느 거래 것인지 구분 불가였다(거래일지 API가
거래별 위험도를 못 내려주던 원인). detect가 저장 시 채우며, 도입 전 행은 NULL.

Revision ID: b3c4d5e6f7a8
Revises: a2b3c4d5e6f7
Create Date: 2026-09-10
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'b3c4d5e6f7a8'
down_revision: Union[str, Sequence[str], None] = 'a2b3c4d5e6f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('analysis_results',
                  sa.Column('trade_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_analysis_results_trade_id', 'analysis_results',
                          'trades', ['trade_id'], ['id'])
    op.create_index('ix_analysis_results_trade_id', 'analysis_results', ['trade_id'])


def downgrade() -> None:
    op.drop_index('ix_analysis_results_trade_id', table_name='analysis_results')
    op.drop_constraint('fk_analysis_results_trade_id', 'analysis_results', type_='foreignkey')
    op.drop_column('analysis_results', 'trade_id')
