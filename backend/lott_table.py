"""
시장 전체 복권성(LOTT) 순위표 로더 — 실계좌 분석이 (적용연, 적용월, 종목코드)로 조회.

표는 ml/train/make_lott_table.py가 만들고(레포에 커밋하지 않음), 서버에는 모델
Release 번들 자산(lott_ranks.csv)으로 함께 내려온다(layer3._RELEASE_ASSETS).
탐색 순서: CANARY_LOTT_TABLE(경로 직접 지정) → CANARY_MODEL_DIR/lott_ranks.csv
(기본 ml/artifacts) → data/lott_ranks.csv(로컬 생성 위치). 없으면 None + 경고 1회 —
features.build_features는 None이면 입력 종목만으로 그 자리 계산하는 옛 경로로 간다.
"""

import logging
import os
import sys
from functools import lru_cache
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

logger = logging.getLogger(__name__)
_warned = False


def _candidates() -> list[Path]:
    env = os.environ.get("CANARY_LOTT_TABLE")
    if env:
        return [Path(env)]
    art_dir = Path(os.environ.get("CANARY_MODEL_DIR", _REPO_ROOT / "ml" / "artifacts"))
    return [art_dir / "lott_ranks.csv", _REPO_ROOT / "data" / "lott_ranks.csv"]


@lru_cache(maxsize=4)
def _load(path: str) -> dict:
    from synthetic_data.market.lott import load_lott_table
    table = load_lott_table(path)
    logger.info("복권성 순위표 로드: %s (%d개월)", path, len(table))
    return table


def get_lott_table() -> dict | None:
    """{(적용연, 적용월): Series(종목코드 -> lott_rank)} 또는 None(표 없음)."""
    global _warned
    for p in _candidates():
        if p.exists():
            return _load(str(p))
    if not _warned:
        logger.warning("복권성 순위표 없음(%s) — 실계좌 lott_rank는 입력 종목만으로 계산",
                       " / ".join(str(p) for p in _candidates()))
        _warned = True
    return None
