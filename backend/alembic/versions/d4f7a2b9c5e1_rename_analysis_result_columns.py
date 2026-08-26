"""analysis_results 컬럼 정리: lstm_score→deep_score, xai_result→detail, final_score 삭제

- lstm_score: 3계층이 LSTM AE에서 GRU 태거로 바뀐 뒤에도 이름이 남아 있었음.
- xai_result: 처음엔 XAI 근거만 담았으나 지금은 거래별 상세 전부(판정·flags·규칙·
  마할라노비스·3계층 근거·분포 점검)를 담는 JSON — 내용에 맞게 detail로.
- final_score: 가중합 판정 폐기(flag 개수 기반) 후 항상 NULL이던 죽은 컬럼.
(2026-08-27, 은우 — 프론트 키 이름도 함께 바뀜: 도경 전달)

Revision ID: d4f7a2b9c5e1
Revises: c3d8e91f6a02
Create Date: 2026-08-27
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'd4f7a2b9c5e1'
down_revision: Union[str, Sequence[str], None] = 'c3d8e91f6a02'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('analysis_results', 'lstm_score', new_column_name='deep_score')
    op.alter_column('analysis_results', 'xai_result', new_column_name='detail')
    op.drop_column('analysis_results', 'final_score')


def downgrade() -> None:
    op.add_column('analysis_results', sa.Column('final_score', sa.Float(), nullable=True))
    op.alter_column('analysis_results', 'detail', new_column_name='xai_result')
    op.alter_column('analysis_results', 'deep_score', new_column_name='lstm_score')
