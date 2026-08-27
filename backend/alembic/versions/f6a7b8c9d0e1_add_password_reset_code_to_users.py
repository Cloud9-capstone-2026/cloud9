"""add password reset code fields to users

비밀번호 재설정(forgot password) 흐름 추가. 이메일 인증 6자리 코드와 같은
방식(HMAC 해시 저장)이지만 컬럼은 분리 — 두 플로우가 서로의 코드를
덮어쓰지 않게 하기 위함(auth.py 주석 참고).

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-08-27
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'f6a7b8c9d0e1'
down_revision: Union[str, Sequence[str], None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('password_reset_code_hash', sa.String(length=64), nullable=True))
    op.add_column('users', sa.Column('password_reset_code_expires_at', sa.TIMESTAMP(), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'password_reset_code_expires_at')
    op.drop_column('users', 'password_reset_code_hash')