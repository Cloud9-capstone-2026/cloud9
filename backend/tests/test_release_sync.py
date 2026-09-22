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
    monkeypatch.setattr(layer3, "_last_refresh_check", None)
    # 갱신 검사(아래 절)가 네트워크를 시도하지만 실패해도 기존 파일 유지
    assert layer3._ensure_artifacts() == art_dir


def test_no_tag_env_uses_local_files(art_dir, monkeypatch):
    monkeypatch.delenv("CANARY_MODEL_RELEASE", raising=False)
    assert layer3._ensure_artifacts() == art_dir  # 로컬 학습 산출물 경로


def test_lott_table_not_in_model_release():
    # 순위표는 고정 태그 Release로 분리(2026-09-02) — 모델 자산 목록에 다시 넣으면
    # 무결성 검증이 월간 갱신된 표를 지문 불일치로 죽이는 회귀가 된다.
    assert "lott_ranks.csv" not in layer3._RELEASE_ASSETS


def test_missing_or_stale_tag_record_redownloads(art_dir, monkeypatch):
    monkeypatch.setenv("CANARY_MODEL_RELEASE", "model-x")
    with pytest.raises(_Boom):  # 기록 없음(옛 배포) → 다운로드 시도 (repo 정의 후 첫 호출)
        layer3._ensure_artifacts()
    (art_dir / "release_tag.txt").write_text("model-old")
    with pytest.raises(_Boom):  # 태그 변경 → 재다운로드 시도
        layer3._ensure_artifacts()


# ── 갱신 검사 (2026-09-22: 고정 태그 + 지문 추적) ──────────────────────────
# 태그 일치여도 쿨다운 주기로 Release의 hashes.json을 로컬과 비교해, 다르면
# 묶음 재다운로드 + 메모리 모델 무효화. 검사 실패는 기존 파일 유지(무영향).

import time
from types import SimpleNamespace


class _FakeResp:
    def __init__(self, json_data=None, content=b""):
        self._json, self.content = json_data, content

    def raise_for_status(self):
        pass

    def json(self):
        return self._json


def _fake_release(hashes_bytes, asset_files):
    """requests.get 대체: 태그 조회 → 자산 목록, 자산 URL → 내용. 호출 URL 기록."""
    calls = []
    assets = [{"name": "hashes.json", "url": "asset://hashes.json"}]
    assets += [{"name": n, "url": f"asset://{n}"} for n in asset_files]
    contents = {"asset://hashes.json": hashes_bytes,
                **{f"asset://{n}": b for n, b in asset_files.items()}}

    def fake_get(url, headers=None, timeout=None):
        calls.append(url)
        if "releases/tags" in url:
            return _FakeResp(json_data={"assets": assets})
        return _FakeResp(content=contents[url])
    return fake_get, calls


@pytest.fixture()
def refresh_env(art_dir, monkeypatch):
    """태그 일치 상태 + 쿨다운 초기화 + 가짜 cache_clear."""
    (art_dir / "release_tag.txt").write_text("model-x")
    (art_dir / "hashes.json").write_bytes(b'{"artifacts": {}}')
    monkeypatch.setenv("CANARY_MODEL_RELEASE", "model-x")
    monkeypatch.setattr(layer3, "_last_refresh_check", None)
    cleared = []
    monkeypatch.setattr(layer3, "_load_artifacts",
                        SimpleNamespace(cache_clear=lambda: cleared.append(1)))
    return art_dir, cleared


def test_refresh_skipped_within_cooldown(refresh_env, monkeypatch):
    art_dir, _ = refresh_env
    monkeypatch.setattr(layer3, "_last_refresh_check", time.monotonic())
    fake_get, calls = _fake_release(b"x", {})
    monkeypatch.setattr(layer3.requests, "get", fake_get)
    assert layer3._ensure_artifacts() == art_dir
    assert calls == []  # 쿨다운 안 — 네트워크 0


def test_refresh_same_fingerprint_keeps_files(refresh_env, monkeypatch):
    art_dir, cleared = refresh_env
    fake_get, calls = _fake_release(b'{"artifacts": {}}', {"tagger.pt": b"NEW"})
    monkeypatch.setattr(layer3.requests, "get", fake_get)
    assert layer3._ensure_artifacts() == art_dir
    assert (art_dir / "tagger.pt").read_bytes() == b"x"  # 재다운로드 없음
    assert cleared == []
    assert len(calls) == 2  # 태그 조회 + hashes.json — 그 이상 안 받음


def test_refresh_changed_fingerprint_redownloads(refresh_env, monkeypatch):
    art_dir, cleared = refresh_env
    fake_get, _ = _fake_release(
        b'{"artifacts": {"note": "changed"}}',
        {"tagger.pt": b"NEW", "tagger_meta.json": b"{}",
         "distribution_ref.json": b"{}"})
    monkeypatch.setattr(layer3.requests, "get", fake_get)
    assert layer3._ensure_artifacts() == art_dir
    assert (art_dir / "tagger.pt").read_bytes() == b"NEW"      # 묶음 교체됨
    assert (art_dir / "release_tag.txt").read_text() == "model-x"
    assert cleared == [1]                                       # 메모리 모델 무효화


def test_refresh_check_failure_keeps_files(refresh_env, monkeypatch):
    art_dir, cleared = refresh_env

    def boom(*a, **k):
        raise _Boom("네트워크 불가")
    monkeypatch.setattr(layer3.requests, "get", boom)
    assert layer3._ensure_artifacts() == art_dir  # 예외 없이 기존 파일
    assert cleared == []
    # 실패도 검사 시각을 남겨 쿨다운 동안 재시도 폭주 방지
    assert layer3._last_refresh_check is not None
