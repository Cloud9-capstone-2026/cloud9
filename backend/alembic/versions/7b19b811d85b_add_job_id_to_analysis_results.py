"""add job_id to analysis_results

Revision ID: 7b19b811d85b
Revises: 08b573070345
Create Date: 2026-08-07 11:28:59.502931

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7b19b811d85b'
down_revision: Union[str, Sequence[str], None] = '08b573070345'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # batch_alter_table: SQLite는 ALTER로 제약을 못 붙여서(테이블 재생성 방식 필요),
    # Postgres(RDS)에서는 일반 ALTER로 그대로 실행됨 — 로컬/운영 DB 둘 다 이 형태로 통일.
    with op.batch_alter_table('analysis_results') as batch_op:
        batch_op.add_column(sa.Column('job_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            'fk_analysis_results_job_id', 'analysis_jobs', ['job_id'], ['id']
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('analysis_results') as batch_op:
        batch_op.drop_constraint('fk_analysis_results_job_id', type_='foreignkey')
        batch_op.drop_column('job_id')
