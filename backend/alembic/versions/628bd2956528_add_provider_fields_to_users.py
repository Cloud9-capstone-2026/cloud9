"""add provider fields to users

Revision ID: 628bd2956528
Revises: a1c4e9f0b213
Create Date: 2026-08-18 00:00:00.000000

alembic/versions/ 에 저장.

[소셜로그인/이메일인증 스키마 설계 - 2026-08-18]
팀 논의로 "옵션A(users 테이블 컬럼 확장)"로 확정됨. 계정당 로그인 수단은
1개로 고정(예: 구글로 가입한 계정은 이메일/비번 로그인 불가) — user_auth_providers
같은 별도 테이블로 계정당 여러 수단을 연결하는 방식(옵션B)은 채택하지 않음.

- provider: 'local' | 'google' | 'kakao' | 'naver'. 로컬(이메일/비번) 계정도
  명시적으로 'local'로 채워서, provider가 NULL인 행이 생기지 않게 한다
  (NULL이면 "아직 provider 개념 도입 전에 만들어진 계정"인지 "로컬 계정"인지
  구분이 안 되는 모호함이 생기므로).
- provider_id: 소셜 로그인 제공자가 발급하는 사용자 고유 ID. 로컬 계정은 NULL.
- email_verified: 이메일 인증 완료 여부. 기본 False.

기존 행 backfill: hashed_password가 있는 행(=지금까지 가입한 로컬 계정)은
provider='local'로 채우고, email_verified=True로 grandfather 처리한다.
이메일 인증 기능 도입 전에 이미 가입한 계정을 갑자기 미인증 취급해
로그인을 막아버리면 안 되기 때문 — 인증 요구는 이 마이그레이션 이후
신규 가입자부터 적용하는 게 맞다고 판단함. hashed_password가 없는 행
(과거 테스트/데모용으로 이름만 넣고 만든 계정)은 provider를 NULL로 남겨둠 —
이런 행은 애초에 로그인 자체가 불가능한 상태라 임의로 'local'을 채우면
오히려 오해를 유발할 수 있음.

provider_id에는 unique 제약을 걸지 않고 (provider, provider_id) 복합
unique로 건다. 두 컬럼 다 NULL인 로컬 계정끼리는 표준 SQL에서 NULL이
서로 다른 값으로 취급되어 유일성 검사에 걸리지 않으므로 문제없다.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '628bd2956528'
down_revision: Union[str, Sequence[str], None] = 'a1c4e9f0b213'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(sa.Column('provider', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('provider_id', sa.String(length=255), nullable=True))
        # server_default='false' — 마이그레이션 시점에 이미 존재하는 행에도
        # 즉시 기본값이 채워지게 함(뒤 UPDATE로 로컬 계정만 다시 True로 덮어씀).
        batch_op.add_column(
            sa.Column('email_verified', sa.Boolean(), nullable=False,
                      server_default=sa.false())
        )
        batch_op.create_unique_constraint(
            'uq_users_provider_provider_id', ['provider', 'provider_id']
        )

    # 기존 로컬 계정 backfill: provider='local', email_verified=True(grandfather)
    op.execute(
        "UPDATE users SET provider = 'local', email_verified = true "
        "WHERE hashed_password IS NOT NULL"
    )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_constraint('uq_users_provider_provider_id', type_='unique')
        batch_op.drop_column('email_verified')
        batch_op.drop_column('provider_id')
        batch_op.drop_column('provider')