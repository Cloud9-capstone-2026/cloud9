"""
alembic 마이그레이션 사슬 검증 — head가 정확히 1개인지.

두 사람이 같은 시기에 마이그레이션을 만들면 같은 부모를 가리키는 파일이 둘 생겨
사슬이 갈라지고, 배포의 `alembic upgrade head`가 "Multiple head revisions"로
죽는다(2026-09-10 실사고: 알림/거래일지(#68)와 trade_id(#69)가 같은 부모 지정 →
#69 배포 실패). 이 테스트는 그 상태를 머지 전 CI에서 잡는다.

alembic 패키지를 import하지 않고 버전 파일을 직접 파싱한다 — CI(requirements.lock)에
alembic이 없어도 돌게. head = 어떤 파일의 down_revision으로도 지목되지 않은 revision.
갈라졌을 때의 수리법: 나중에 만든 파일의 down_revision을 다른 갈래의 끝으로 재지정.
"""

import re
from pathlib import Path

_VERSIONS = Path(__file__).resolve().parents[1] / "alembic" / "versions"


def _field(text: str, name: str) -> str | None:
    m = re.search(rf"^{name}(?::[^=]*)?\s*=\s*['\"]([0-9a-f]+)['\"]", text, re.M)
    return m.group(1) if m else None


def test_single_migration_head():
    files = sorted(_VERSIONS.glob("*.py"))
    assert files, "마이그레이션 파일이 없음 — 경로 확인"
    revisions, parents = {}, set()
    for f in files:
        text = f.read_text(encoding="utf-8")
        rev = _field(text, "revision")
        assert rev, f"{f.name}: revision 식별자를 못 읽음"
        revisions[rev] = f.name
        down = _field(text, "down_revision")  # None(베이스)이면 부모 없음
        if down:
            parents.add(down)

    unknown = parents - set(revisions)
    assert not unknown, f"존재하지 않는 revision을 부모로 지정: {unknown}"

    heads = {rev: name for rev, name in revisions.items() if rev not in parents}
    assert len(heads) == 1, (
        f"마이그레이션 head가 {len(heads)}개: {heads} — 사슬이 갈라짐. "
        "나중에 만든 파일의 down_revision을 다른 갈래의 끝으로 재지정할 것")
