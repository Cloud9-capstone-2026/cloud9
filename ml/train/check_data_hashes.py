"""
데이터 지문 대조 (단계 1b): 이 환경의 시세 캐시·데이터셋이 아티팩트를 만든
환경과 동일한지 hashes.json과 SHA-256으로 대조한다.

실행: python -m ml.train.check_data_hashes [hashes.json 경로]   (레포 루트에서)

용도: 팀 드라이브에서 받은 .cache/dataset을 배치한 뒤 실행 — 전부 OK면
그 환경에서 생성기·학습을 돌려도 바이트 단위 재현이 성립한다.
불일치가 나오면 KRX 소급 수정 또는 파일 전달 사고를 의심할 것.
"""

import hashlib
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fp:
        for chunk in iter(lambda: fp.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    ref_path = Path(sys.argv[1]) if len(sys.argv) > 1 else (
        _REPO / "ml" / "artifacts" / "hashes.json")
    with open(ref_path, encoding="utf-8") as fp:
        ref = json.load(fp)

    groups = {
        "files": {".cache/": _REPO / "synthetic_data" / ".cache",
                  "": _REPO},  # 접두사 → 기준 디렉터리
        "dataset": {"": _REPO / "dataset"},
    }
    n_ok = n_bad = n_missing = 0
    for section, prefix_map in groups.items():
        for rel, want in ref.get(section, {}).items():
            for prefix, base in prefix_map.items():
                if rel.startswith(prefix):
                    p = base / rel[len(prefix):]
                    break
            if not p.exists():
                print(f"  없음      {rel}")
                n_missing += 1
                continue
            got = sha256(p)
            if got == want:
                n_ok += 1
            else:
                print(f"  불일치    {rel}")
                n_bad += 1

    total = n_ok + n_bad + n_missing
    print(f"\n대조 {total}건: 일치 {n_ok} / 불일치 {n_bad} / 없음 {n_missing}")
    if n_bad == n_missing == 0:
        print("전부 일치 — 바이트 재현 가능 환경")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
