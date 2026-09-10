"""add notifications table

분석 job 상태(done/failed) 변경 시 알림 1행을 쌓기 위한 테이블.
GET /notifications(목록+안읽음수),
POST /notifications/{id}/read. 생성 트리거는 pipeline/jobs.py의
run_analysis_job이 상태 전이 직후 직접 담당(폴링 대체 목적, 별도 워커 없음).

Revision ID: b7c1d4e8f2a9
Revises: a2b3c4d5e6f7
Create Date: 2026-09-09
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'b7c1d4e8f2a9'
down_revision: Union[str, Sequence[str], None] = 'a2b3c4d5e6f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'notifications',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('type', sa.String(length=30), nullable=False),
        sa.Column('message', sa.String(length=255), nullable=False),
        sa.Column('job_id', sa.Integer(), sa.ForeignKey('analysis_jobs.id'), nullable=True),
        sa.Column('upload_id', sa.Integer(), sa.ForeignKey('csv_uploads.id'), nullable=True),
        sa.Column('is_read', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.func.now()),
    )
    op.create_index('ix_notifications_user_id', 'notifications', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_notifications_user_id', table_name='notifications')
    op.drop_table('notifications')