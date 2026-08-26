"""add email verification code fields to users

딥링크(JWT 토큰) 방식 → 6자리 숫자 코드 방식으로 전환 (2026-08-24 결정).
코드 원문은 저장하지 않고 HMAC-SHA256 해시만 저장한다(비밀번호와 달리
브루트포스 방지가 레이트리밋 의존적이라 해시 자체는 빠른 방식 사용).

Revision ID: 9f2a1c7d4e88
Revises: 628bd2956528
Create Date: 2026-08-26
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '9f2a1c7d4e88'
down_revision: Union[str, Sequence[str], None] = '628bd2956528'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('verification_code_hash', sa.String(length=64), nullable=True))
    op.add_column('users', sa.Column('verification_code_expires_at', sa.TIMESTAMP(), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'verification_code_expires_at')
    op.drop_column('users', 'verification_code_hash')