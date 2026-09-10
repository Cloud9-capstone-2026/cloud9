"""add dart_disclosures table

OpenDART 공시 목록 캐시. 홈 '오늘의 주요 소식'/'전체 소식', 리포트 상세
'관련 공시·뉴스' 3곳이 이 캐시만 조회한다(요청마다 OpenDART 직접 호출 안 함
— 일 1만 콜 쿼터 보호 + 응답속도).

Revision ID: e1f4b8c9a2d7
Revises: d8a2c5e7f1b3
Create Date: 2026-09-09
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'e1f4b8c9a2d7'
down_revision: Union[str, Sequence[str], None] = 'd8a2c5e7f1b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'dart_disclosures',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('rcept_no', sa.String(length=20), unique=True, nullable=False),
        sa.Column('corp_name', sa.String(length=100), nullable=False),
        sa.Column('report_type', sa.String(length=100), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('disclosure_date', sa.Date(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.func.now()),
    )
    op.create_index('ix_dart_disclosures_corp_name', 'dart_disclosures', ['corp_name'])
    op.create_index('ix_dart_disclosures_disclosure_date', 'dart_disclosures', ['disclosure_date'])


def downgrade() -> None:
    op.drop_index('ix_dart_disclosures_disclosure_date', table_name='dart_disclosures')
    op.drop_index('ix_dart_disclosures_corp_name', table_name='dart_disclosures')
    op.drop_table('dart_disclosures')