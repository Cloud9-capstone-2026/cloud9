"""add user_rules and upload_files tables

은우 요청 반영 (2026-08-27):
1) user_rules — 1계층 사용자 정의 규칙 파라미터 (2026-08-07 회의 결정,
   pipeline/user_rules.py가 이미 이 스키마를 기대하며 구현돼 있었음)
2) upload_files — CSV 원본 파일을 EC2 디스크 대신 DB에 보관
   (pipeline/upload_store.py가 이미 이 스키마를 기대하며 구현돼 있었음)

두 테이블 모두 이 마이그레이션 전에는 관련 코드가 getattr로 존재 여부를
확인해 없으면 기존 동작(기본 규칙 조합 / 디스크 저장)으로 폴백하도록
방어적으로 짜여 있었으므로, 이 마이그레이션 적용 자체는 기존 동작을
깨뜨리지 않고 새 경로를 "켜는" 것에 가깝다.

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-08-27
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, Sequence[str], None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'user_rules',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('rule_id', sa.String(length=30), nullable=False),
        sa.Column('param', sa.Float(), nullable=True),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.func.now()),
        sa.UniqueConstraint('user_id', 'rule_id', name='uq_user_rules_user_id_rule_id'),
    )
    op.create_index('ix_user_rules_user_id', 'user_rules', ['user_id'])

    op.create_table(
        'upload_files',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('upload_id', sa.Integer(), sa.ForeignKey('csv_uploads.id'), unique=True, nullable=False),
        sa.Column('content', sa.LargeBinary(), nullable=False),
        sa.Column('size', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('upload_files')
    op.drop_index('ix_user_rules_user_id', table_name='user_rules')
    op.drop_table('user_rules')