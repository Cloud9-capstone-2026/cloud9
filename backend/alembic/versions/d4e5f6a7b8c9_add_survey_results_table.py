"""add survey_results table

투자 성향 자가진단(20문항, 4축) 결과 저장 테이블. 스펙 확정일 2026-08-17,
구현 착수 2026-08-26.

Revision ID: d4e5f6a7b8c9
Revises: c3d8e91f6a02
Create Date: 2026-08-26
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, Sequence[str], None] = 'c3d8e91f6a02'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'survey_results',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('disposition_strength_raw', sa.Integer(), nullable=False),
        sa.Column('disposition_strength_normalized', sa.Float(), nullable=False),
        sa.Column('disposition_strength_level', sa.String(length=4), nullable=False),
        sa.Column('overconfidence_raw', sa.Integer(), nullable=False),
        sa.Column('overconfidence_normalized', sa.Float(), nullable=False),
        sa.Column('overconfidence_level', sa.String(length=4), nullable=False),
        sa.Column('lottery_preference_raw', sa.Integer(), nullable=False),
        sa.Column('lottery_preference_normalized', sa.Float(), nullable=False),
        sa.Column('lottery_preference_level', sa.String(length=4), nullable=False),
        sa.Column('herd_sensitivity_raw', sa.Integer(), nullable=False),
        sa.Column('herd_sensitivity_normalized', sa.Float(), nullable=False),
        sa.Column('herd_sensitivity_level', sa.String(length=4), nullable=False),
        sa.Column('type_code', sa.String(length=4), nullable=False),
        sa.Column('answers', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.func.now()),
    )
    # id는 PRIMARY KEY라 이미 자동으로 인덱스가 생기므로 별도 생성 불필요.
    # user_id는 조회 빈도가 높을 것이라(본인 최신 결과 조회 등) 명시적으로 추가.
    op.create_index('ix_survey_results_user_id', 'survey_results', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_survey_results_user_id', table_name='survey_results')
    op.drop_table('survey_results')