"""
모델 Release 동기화(layer3._ensure_artifacts) — 네트워크 0 (전부 가짜 응답).

고정하는 것 (2026-09-23 v2 — 최신 model-* Release 추종):
- 운영 상태(파일+기록)는 쿨다운 주기로 목록을 조회해 최신 태그를 따라간다
- 최신 == 기록이면 무변경, 새 태그면 묶음 교체 + 메모리 모델 무효화
- 조회 실패는 기존 파일 유지(서비스 무영향), 부트스트랩은 env 태그 폴백
- 태그 기록·env 모두 없으면 로컬 학습 산출물 사용
"""

import time
from types import SimpleNamespace

import pytest

from models import layer3


class _Boom(Exception):
    pass


@pytest.fixture()
def art_dir(tmp_path, monkeypatch):
    (tmp_path / "tagger.pt").write_bytes(b"x")
    (tmp_path / "tagger_meta.json").write_text("{}")
    monkeypatch.setattr(layer3, "_ART_DIR", tmp_path)
    monkeypatch.setattr(layer3, "_last_refresh_check", None)

    def no_network(*a, **k):
        raise _Boom("네트워크 호출")
    monkeypatch.setattr(layer3.requests, "get", no_network)
    return tmp_path


def test_no_tag_env_uses_local_files(art_dir, monkeypatch):
    monkeypatch.delenv("CANARY_MODEL_RELEASE", raising=False)
    assert layer3._ensure_artifacts() == art_dir  # 로컬 학습 산출물 경로


def test_lott_table_not_in_model_release():
    # 순위표는 고정 태그 Release로 분리(2026-09-02) — 모델 자산 목록에 다시 넣으면
    # 무결성 검증이 월간 갱신된 표를 지문 불일치로 죽이는 회귀가 된다.
    assert "lott_ranks.csv" not in layer3._RELEASE_ASSETS


def test_bootstrap_falls_back_to_env_tag(art_dir, monkeypatch):
    """기록 없는 옛 파일 + 목록 조회 실패 → env 태그로 다운로드 시도 (부트스트랩 폴백)."""
    monkeypatch.setenv("CANARY_MODEL_RELEASE", "model-x")
    with pytest.raises(_Boom):  # 목록 조회 실패(경고 후) → env 태그 자산 조회 시도에서 실패
        layer3._ensure_artifacts()


def test_check_failure_keeps_files(art_dir, monkeypatch):
    """운영 상태에서 목록 조회 실패 → 예외 없이 기존 파일 유지 + 검사 시각 기록."""
    (art_dir / "release_tag.txt").write_text("model-x")
    monkeypatch.setenv("CANARY_MODEL_RELEASE", "model-x")
    assert layer3._ensure_artifacts() == art_dir  # no_network가 터져도 유지
    assert layer3._last_refresh_check is not None  # 쿨다운 동안 재시도 폭주 방지


# ── 최신 추종 (가짜 Release 목록·자산) ─────────────────────────────────────

class _FakeResp:
    def __init__(self, json_data=None, content=b""):
        self._json, self.content = json_data, content

    def raise_for_status(self):
        pass

    def json(self):
        return self._json


def _fake_github(releases, asset_files):
    """requests.get 대체: 목록 조회 → releases, 태그 조회 → 자산 목록, 자산 → 내용."""
    calls = []
    assets = [{"name": n, "url": f"asset://{n}"} for n in asset_files]

    def fake_get(url, headers=None, timeout=None):
        calls.append(url)
        if "/releases?" in url:
            return _FakeResp(json_data=releases)
        if "releases/tags" in url:
            return _FakeResp(json_data={"assets": assets})
        return _FakeResp(content=asset_files[url.replace("asset://", "")])
    return fake_get, calls


@pytest.fixture()
def tracking_env(art_dir, monkeypatch):
    """운영 상태(기록 model-20260920) + 가짜 cache_clear."""
    (art_dir / "release_tag.txt").write_text("model-20260920")
    monkeypatch.setenv("CANARY_MODEL_RELEASE", "model-20260920")
    cleared = []
    monkeypatch.setattr(layer3, "_load_artifacts",
                        SimpleNamespace(cache_clear=lambda: cleared.append(1)))
    return art_dir, cleared


def test_skipped_within_cooldown(tracking_env, monkeypatch):
    art_dir, _ = tracking_env
    monkeypatch.setattr(layer3, "_last_refresh_check", time.monotonic())
    fake_get, calls = _fake_github([], {})
    monkeypatch.setattr(layer3.requests, "get", fake_get)
    assert layer3._ensure_artifacts() == art_dir
    assert calls == []  # 쿨다운 안 — 네트워크 0


def test_latest_equals_recorded_keeps_files(tracking_env, monkeypatch):
    art_dir, cleared = tracking_env
    fake_get, calls = _fake_github(
        [{"tag_name": "model-20260920"}, {"tag_name": "model-20260805"}], {})
    monkeypatch.setattr(layer3.requests, "get", fake_get)
    assert layer3._ensure_artifacts() == art_dir
    assert (art_dir / "tagger.pt").read_bytes() == b"x"  # 무변경
    assert cleared == []
    assert len(calls) == 1  # 목록 조회 1콜에서 끝


def test_newer_release_triggers_download(tracking_env, monkeypatch):
    art_dir, cleared = tracking_env
    fake_get, _ = _fake_github(
        [{"tag_name": "model-20260922"}, {"tag_name": "model-20260920"}],
        {"tagger.pt": b"NEW", "tagger_meta.json": b"{}",
         "distribution_ref.json": b"{}", "hashes.json": b'{"artifacts": {}}'})
    monkeypatch.setattr(layer3.requests, "get", fake_get)
    assert layer3._ensure_artifacts() == art_dir
    assert (art_dir / "tagger.pt").read_bytes() == b"NEW"                 # 묶음 교체
    assert (art_dir / "release_tag.txt").read_text() == "model-20260922"  # 버전 기록 갱신
    assert cleared == [1]                                                 # 메모리 모델 무효화


def test_latest_ignores_drafts_and_other_releases(tracking_env, monkeypatch):
    """model-* 아닌 태그(순위표 등)와 초안은 최신 선정에서 제외 — 같은 날 접미사는 사전순."""
    art_dir, cleared = tracking_env
    fake_get, _ = _fake_github(
        [{"tag_name": "lott-table"},                          # 접두사 불일치 — 무시
         {"tag_name": "model-20260930", "draft": True},       # 초안 — 무시
         {"tag_name": "model-20260922b"},                     # 같은 날 재배포 — 최신
         {"tag_name": "model-20260922"}],
        {"tagger.pt": b"NEW2", "tagger_meta.json": b"{}"})
    monkeypatch.setattr(layer3.requests, "get", fake_get)
    layer3._ensure_artifacts()
    assert (art_dir / "release_tag.txt").read_text() == "model-20260922b"
    assert cleared == [1]
