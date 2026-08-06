"""
재현성 박제 (단계 1b): 모델 아티팩트가 "무엇으로 만들어졌는지"의 지문을 기록한다.

실행: python -m ml.train.make_hashes [--data-tree D:/path]   (레포 루트에서)

산출: ml/artifacts/hashes.json
- files   : 시세·지수 캐시 parquet 전체, config.py, universe_frozen.py,
            requirements.lock의 SHA-256 (아티팩트 트리 기준)
- dataset : manifest + 데이터셋 CSV 전체의 SHA-256
- data_tree_files : (--data-tree 지정 시) 데이터 생성 트리의 생성기 입력
            (config.py·universe_frozen.py) 해시 + 아티팩트 트리와의 일치 여부 —
            git 상태만으로는 두 트리의 파일 동일성을 증명 못 하는 빈틈 보완
- artifacts : 출력물(tagger.pt·tagger_meta.json·distribution_ref.json)의 SHA-256
            — Release 다운로드 무결성 검증용(layer3._ensure_artifacts가 대조)
- 코드 상태(Git SHA·브랜치·dirty) 두 트리 분리 기록 + Python 버전
부수 효과: tagger_meta.json에 dataset_manifest_hash·seqfeat_spec·hashes_ref를
추가한다. 메타 보강을 먼저 하고 출력물 해시를 마지막에 계산한다(자기 무효화 방지)
— 따라서 이 스크립트는 아티팩트 생성 파이프라인의 맨 끝에서 실행해야 한다.

주의: KRX 수정주가는 소급 변경될 수 있어, 캐시 parquet 해시가 곧 "재현의 기준점"이다
(같은 해시의 캐시를 가진 환경 = 바이트 재현 가능). 대조는 check_data_hashes.py.
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))

from synthetic_data import config  # noqa: E402
from ml import seqfeat  # noqa: E402

ART_DIR = _REPO / "ml" / "artifacts"
CACHE = _REPO / "synthetic_data" / ".cache"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fp:
        for chunk in iter(lambda: fp.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_state(tree: Path) -> dict:
    def run(*args):
        return subprocess.run(["git", "-C", str(tree), *args],
                              capture_output=True, text=True).stdout.strip()
    return {
        "branch": run("rev-parse", "--abbrev-ref", "HEAD"),
        "sha": run("rev-parse", "HEAD"),
        "dirty": bool(run("status", "--porcelain")),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-tree", default=None,
                    help="데이터를 생성한 작업 트리 경로 (별도 브랜치에서 생성한 경우)")
    args = ap.parse_args()

    files = {}
    for p in sorted(CACHE.glob("*.parquet")):
        files[f".cache/{p.name}"] = sha256(p)
    for rel in ["synthetic_data/config.py",
                "synthetic_data/market/universe_frozen.py",
                "requirements.lock"]:
        p = _REPO / rel
        if p.exists():
            files[rel] = sha256(p)

    dataset = {}
    manifest = _REPO / config.DATASET_DIR / "manifest.csv"
    dataset["manifest.csv"] = sha256(manifest)
    for kind in config.DATASET_KINDS:
        for p in sorted((_REPO / config.DATASET_DIR / kind).glob("*.csv")):
            dataset[f"{kind}/{p.name}"] = sha256(p)

    # 데이터 생성 트리의 생성기 입력 파일 — git 상태가 아니라 내용 자체를 대조
    data_tree_files = None
    if args.data_tree:
        data_tree_files = {}
        for rel in ["synthetic_data/config.py",
                    "synthetic_data/market/universe_frozen.py"]:
            p = Path(args.data_tree) / rel
            if p.exists():
                h = sha256(p)
                data_tree_files[rel] = {
                    "sha256": h,
                    "matches_artifacts_tree": files.get(rel) == h,
                }

    # 1) 메타 보강을 먼저 — 그다음 출력물 해시 (자기 무효화 방지)
    meta_path = ART_DIR / "tagger_meta.json"
    with open(meta_path, encoding="utf-8") as fp:
        meta = json.load(fp)
    meta["dataset_manifest_hash"] = dataset["manifest.csv"]
    meta["seqfeat_spec"] = "v1_17ch"
    meta["hashes_ref"] = "hashes.json"
    with open(meta_path, "w", encoding="utf-8") as fp:
        json.dump(meta, fp, ensure_ascii=False, indent=2)
    print("tagger_meta.json 보강 완료 (manifest hash + seqfeat_spec)")

    # 2) 출력물 지문 — Release 다운로드 검증(layer3)이 이 섹션을 대조한다
    artifacts = {}
    for name in ["tagger.pt", "tagger_meta.json", "distribution_ref.json"]:
        p = ART_DIR / name
        if p.exists():
            artifacts[name] = sha256(p)

    out = {
        "created": None,  # 기록 시각은 커밋/PROCESS.md가 담당 (스크립트는 결정적 출력)
        "python": sys.version.split()[0],
        "artifacts_tree": git_state(_REPO),
        "data_tree": git_state(Path(args.data_tree)) if args.data_tree else None,
        "data_tree_files": data_tree_files,
        "seqfeat_spec": {"version": "v1_17ch",
                         "n_channels": seqfeat.N_CHANNELS,
                         "base_features": seqfeat.BASE_FEATURES},
        "files": files,
        "dataset": dataset,
        "artifacts": artifacts,
    }
    ART_DIR.mkdir(parents=True, exist_ok=True)
    out_path = ART_DIR / "hashes.json"
    with open(out_path, "w", encoding="utf-8") as fp:
        json.dump(out, fp, ensure_ascii=False, indent=2)
    print(f"hashes.json → {out_path} "
          f"(입력 {len(files)} + 데이터셋 {len(dataset)} + 출력물 {len(artifacts)})")
    if data_tree_files:
        for rel, info in data_tree_files.items():
            tag = "일치" if info["matches_artifacts_tree"] else "불일치(주의!)"
            print(f"  data-tree {rel}: 아티팩트 트리와 {tag}")


if __name__ == "__main__":
    main()
