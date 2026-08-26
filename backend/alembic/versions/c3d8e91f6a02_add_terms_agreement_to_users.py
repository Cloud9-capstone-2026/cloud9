"""add terms agreement fields to users

회원가입 시 이용약관/개인정보처리방침 동의 여부 기록 (2026-08-26, 도경과 협의).

Revision ID: c3d8e91f6a02
Revises: 9f2a1c7d4e88
Create Date: 2026-08-26
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c3d8e91f6a02'
down_revision: Union[str, Sequence[str], None] = '9f2a1c7d4e88'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('agreed_terms', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('users', sa.Column('agreed_terms_at', sa.TIMESTAMP(), nullable=True))
    # 컬럼 추가 후에는 server_default를 유지할 필요가 없음 — 애플리케이션
    # 코드가 항상 명시적으로 값을 넣으므로, DB 기본값은 과거 데이터 채우기용.
    op.alter_column('users', 'agreed_terms', server_default=None)


def downgrade() -> None:
    op.drop_column('users', 'agreed_terms_at')
    op.drop_column('users', 'agreed_terms')