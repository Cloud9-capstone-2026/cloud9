"""rule_change_logs 테이블 추가 — 1계층 규칙 설정 변경 이력

user_rules는 (user_id, rule_id)당 1행을 덮어써 "언제 켰는지"가 남지 않는다.
진단→규칙 추천→재업로드 효과 측정에서 규칙을 켠 시점이 비교 기준점이라,
변경마다 1행씩 쌓는 append-only 로그를 둔다. 새 테이블 추가만 하는 안전한
변경이다.

Revision ID: c9e2f4a6b8d1
Revises: b3c4d5e6f7a8
Create Date: 2026-10-03
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'c9e2f4a6b8d1'
down_revision: Union[str, Sequence[str], None] = 'b3c4d5e6f7a8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'rule_change_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('rule_id', sa.String(length=30), nullable=False),
        sa.Column('action', sa.String(length=10), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.Column('param', sa.Float(), nullable=True),
        sa.Column('source', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_rule_change_logs_id', 'rule_change_logs', ['id'])
    op.create_index('ix_rule_change_logs_user_id', 'rule_change_logs', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_rule_change_logs_user_id', table_name='rule_change_logs')
    op.drop_index('ix_rule_change_logs_id', table_name='rule_change_logs')
    op.drop_table('rule_change_logs')