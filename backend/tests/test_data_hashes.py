"""
데이터·모델 지문 대조 (느린 층) — 실행: pytest -m slow

로컬의 시세 캐시·설정·데이터셋·모델 아티팩트가 재현성 박제(hashes.json)와
바이트 단위로 일치하는지 검사한다. 어긋난 데이터 위에서 실험·학습을 이어가는
사고 방지용 — ml.train.check_data_hashes와 같은 판정을 테스트로 감싼 것.

전제: hashes.json과 대조 대상 파일들이 로컬에 존재 — 없으면 skip
(데이터를 안 받은 팀원 환경에서 실패로 오인되지 않게).
"""

import hashlib
import json
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.slow

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

_HASHES = _REPO / "ml" / "artifacts" / "hashes.json"
if not _HASHES.exists():
    pytest.skip("hashes.json 없음 — 박제 파일 미보유 환경", allow_module_level=True)
if not (_REPO / "dataset" / "manifest.csv").exists():
    pytest.skip("dataset 없음 — 데이터 미보유 환경", allow_module_level=True)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fp:
        for chunk in iter(lambda: fp.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def test_local_files_match_frozen_hashes():
    with open(_HASHES, encoding="utf-8") as fp:
        ref = json.load(fp)

    # 접두사 → 기준 디렉터리 (ml.train.check_data_hashes와 동일 규약)
    groups = {
        "files": {".cache/": _REPO / "synthetic_data" / ".cache", "": _REPO},
        "dataset": {"": _REPO / "dataset"},
    }
    bad = []
    for section, prefix_map in groups.items():
        for rel, want in ref.get(section, {}).items():
            for prefix, base in prefix_map.items():
                if rel.startswith(prefix):
                    p = base / rel[len(prefix):]
                    break
            if not p.exists():
                bad.append(f"없음: {rel}")
            elif _sha256(p) != want:
                bad.append(f"불일치: {rel}")

    assert not bad, (
        "로컬 데이터가 박제 지문과 어긋남 — KRX 소급 수정 또는 파일 변조 의심:\n  "
        + "\n  ".join(bad))
