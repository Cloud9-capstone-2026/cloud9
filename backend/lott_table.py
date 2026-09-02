"""
시장 전체 복권성(LOTT) 순위표 로더 — 실계좌 분석이 (적용연, 적용월, 종목코드)로 조회.

표는 ml/train/make_lott_table.py가 만들고(레포에 커밋하지 않음), 고정 태그 Release
(기본 lott-table, env CANARY_LOTT_RELEASE)의 자산 lott_ranks.csv로 배포한다.
모델 Release와 분리한 이유: 매월 갱신되는 표를 모델과 묶으면 갱신마다 새 태그 발행 +
서버 env 변경(CANARY_MODEL_RELEASE)이 필요했다. 태그를 고정하고 자산만 교체하면
서버가 아래 신선도 판정으로 알아서 새 표를 받는다(2026-09-02 분리).

탐색 순서: CANARY_LOTT_TABLE(경로 직접 지정 — 다운로드 안 함, 테스트용) →
CANARY_MODEL_DIR/lott_ranks.csv(기본 ml/artifacts) → data/lott_ranks.csv(로컬 생성 위치).

신선도: 로드한 표에 이번 달(적용월) 키가 없으면 Release에서 재다운로드를 시도한다.
실패하거나 새 표에도 이번 달이 없으면 기존 표를 그대로 쓴다 — 이번 달 거래의
lott_rank는 features 쪽 폴백대로 NaN(분석은 계속된다). 실패 후 1시간은 재시도하지
않는다(분석마다 GitHub API를 때리지 않게). 표가 아예 없으면 None + 경고 1회 —
features.build_features는 None이면 입력 종목만으로 그 자리 계산하는 옛 경로로 간다.
"""

import datetime
import logging
import os
import sys
import time
from functools import lru_cache
from pathlib import Path

import requests

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

logger = logging.getLogger(__name__)
_warned = False
_RETRY_COOLDOWN_SEC = 3600
_last_download_try: float | None = None  # 마지막 다운로드 시도 시각(성공/실패 무관)


def _candidates() -> list[Path]:
    env = os.environ.get("CANARY_LOTT_TABLE")
    if env:
        return [Path(env)]
    art_dir = Path(os.environ.get("CANARY_MODEL_DIR", _REPO_ROOT / "ml" / "artifacts"))
    return [art_dir / "lott_ranks.csv", _REPO_ROOT / "data" / "lott_ranks.csv"]


@lru_cache(maxsize=8)
def _load(path: str, mtime: float) -> dict:
    """mtime을 캐시 키에 포함 — 같은 경로에 새 파일을 받아도 다시 읽힌다."""
    from synthetic_data.market.lott import load_lott_table
    table = load_lott_table(path)
    logger.info("복권성 순위표 로드: %s (%d개월)", path, len(table))
    return table


def _is_stale(table: dict) -> bool:
    today = datetime.date.today()
    return (today.year, today.month) not in table


def _download() -> bool:
    """고정 태그 Release에서 lott_ranks.csv를 받아 1순위 경로에 원자 교체. 성공 여부 반환."""
    tag = os.environ.get("CANARY_LOTT_RELEASE", "lott-table")
    from config.settings import get
    repo = get("model.repo", "Cloud9-capstone-2026/cloud9", env_override="CANARY_MODEL_REPO")
    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        r = requests.get(f"https://api.github.com/repos/{repo}/releases/tags/{tag}",
                         headers=headers, timeout=30)
        r.raise_for_status()
        assets = {a["name"]: a for a in r.json().get("assets", [])}
        if "lott_ranks.csv" not in assets:
            logger.warning("Release %s에 lott_ranks.csv 없음", tag)
            return False
        dl = requests.get(assets["lott_ranks.csv"]["url"],
                          headers={**headers, "Accept": "application/octet-stream"},
                          timeout=300)
        dl.raise_for_status()
    except requests.RequestException as e:
        logger.warning("복권성 순위표 다운로드 실패(%s): %r", tag, e)
        return False
    dest = _candidates()[0]
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".csv.tmp")
    tmp.write_bytes(dl.content)
    tmp.replace(dest)  # 부분 다운로드가 정본이 되지 않도록 원자 교체
    logger.info("복권성 순위표 다운로드 완료: %s → %s", tag, dest)
    return True


def _load_first() -> dict | None:
    for p in _candidates():
        if p.exists():
            return _load(str(p), p.stat().st_mtime)
    return None


def get_lott_table() -> dict | None:
    """{(적용연, 적용월): Series(종목코드 -> lott_rank)} 또는 None(표 없음)."""
    global _warned, _last_download_try
    table = _load_first()

    # 신선도 판정 + 자체 갱신. CANARY_LOTT_TABLE(테스트·수동 지정)은 그대로 신뢰.
    if not os.environ.get("CANARY_LOTT_TABLE"):
        if (table is None or _is_stale(table)) \
                and (_last_download_try is None
                     or time.monotonic() - _last_download_try > _RETRY_COOLDOWN_SEC):
            _last_download_try = time.monotonic()
            if _download():
                new = _load_first()
                if new is not None and not _is_stale(new):
                    return new
                if new is not None:  # 받았는데도 이번 달 없음 — 갱신 전. 새 표라도 쓴다.
                    logger.warning("다운로드한 순위표에 이번 달 적용월 없음 — 갱신 필요")
                    return new
            if table is not None and _is_stale(table):
                logger.warning("복권성 순위표가 낡음(이번 달 없음) — 해당 월 lott_rank는 결측 처리")

    if table is None and not _warned:
        logger.warning("복권성 순위표 없음(%s) — 실계좌 lott_rank는 입력 종목만으로 계산",
                       " / ".join(str(p) for p in _candidates()))
        _warned = True
    return table
