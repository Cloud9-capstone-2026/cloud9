"""add auth fields to users

Revision ID: a1c4e9f0b213
Revises: 7b19b811d85b
Create Date: 2026-08-17 00:00:00.000000

alembic/versions/ 에 저장.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1c4e9f0b213'
down_revision: Union[str, Sequence[str], None] = '7b19b811d85b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # nullable=True로 추가: 기존 테스트용 users row(비밀번호 없이 생성된 데모 계정)가
    # 있을 수 있으므로 NOT NULL 제약을 바로 걸면 마이그레이션이 실패한다.
    # 실제 서비스 시작 전(신규 유저만 존재하는 시점)에 NOT NULL로 조이는 후속
    # 마이그레이션을 추가하는 걸 권장.
    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(sa.Column('email', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('hashed_password', sa.String(length=255), nullable=True))
        batch_op.create_unique_constraint('uq_users_email', ['email'])


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_constraint('uq_users_email', type_='unique')
        batch_op.drop_column('hashed_password')
        batch_op.drop_column('email')