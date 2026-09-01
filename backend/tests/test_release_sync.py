"""
모델 Release 태그 동기화(layer3._ensure_artifacts) — 네트워크 0.

고정하는 것: 선언 태그와 기록(release_tag.txt)이 일치하면 네트워크 없이 기존 파일 사용 /
기록이 없거나 다르면 재다운로드 시도(옛 파일이 태그 변경을 무시하던 구멍, #54의
repo 미정의 NameError 회귀 포함) / 태그 미설정이면 파일만 있으면 사용.
"""

import pytest

from models import layer3


class _Boom(Exception):
    pass


@pytest.fixture()
def art_dir(tmp_path, monkeypatch):
    (tmp_path / "tagger.pt").write_bytes(b"x")
    (tmp_path / "tagger_meta.json").write_text("{}")
    monkeypatch.setattr(layer3, "_ART_DIR", tmp_path)

    def no_network(*a, **k):
        raise _Boom("네트워크 호출")
    monkeypatch.setattr(layer3.requests, "get", no_network)
    return tmp_path


def test_matching_tag_uses_local_files(art_dir, monkeypatch):
    (art_dir / "release_tag.txt").write_text("model-x")
    monkeypatch.setenv("CANARY_MODEL_RELEASE", "model-x")
    assert layer3._ensure_artifacts() == art_dir  # 네트워크 없이 반환


def test_no_tag_env_uses_local_files(art_dir, monkeypatch):
    monkeypatch.delenv("CANARY_MODEL_RELEASE", raising=False)
    assert layer3._ensure_artifacts() == art_dir  # 로컬 학습 산출물 경로


def test_missing_or_stale_tag_record_redownloads(art_dir, monkeypatch):
    monkeypatch.setenv("CANARY_MODEL_RELEASE", "model-x")
    with pytest.raises(_Boom):  # 기록 없음(옛 배포) → 다운로드 시도 (repo 정의 후 첫 호출)
        layer3._ensure_artifacts()
    (art_dir / "release_tag.txt").write_text("model-old")
    with pytest.raises(_Boom):  # 태그 변경 → 재다운로드 시도
        layer3._ensure_artifacts()
