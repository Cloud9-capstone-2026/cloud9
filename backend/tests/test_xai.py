"""
XAI(IG) 수학 성질 테스트 — 가짜 태거(고정 시드, 학습 안 됨)로 모델 파일·네트워크
비의존. 학습된 모델이 아니어도 IG의 성질(인과성·완전성)은 모델 무관하게 성립해야
하므로 검증에 충분하다.

고정하는 성질:
  인과성  단방향 GRU → 거래 t의 점수에 t 이후 시점 기여는 정확히 0
  완전성  기여도 총합 ≈ 로짓(입력) − 로짓(기준선)  (IG의 수학적 성질)
  불변성  배치 쪼개기(batch_cap)와 무관하게 같은 결과, 같은 입력 → 같은 출력
"""

import pytest

torch = pytest.importorskip("torch", reason="torch 미설치 환경 — layer3 자체가 비활성")

from ml import seqfeat
from ml.gru_model import GRUTagger
from models.xai import CHANNELS, FEATURE_NAMES, evidence_summary, trade_attributions

N_TARGETS = 4
T, L = 12, 9  # 시퀀스 길이(패딩 포함) / 유효 거래 수


@pytest.fixture(scope="module")
def model():
    torch.manual_seed(0)
    m = GRUTagger(seqfeat.N_CHANNELS, 8, 1, N_TARGETS)
    m.eval()
    return m


@pytest.fixture(scope="module")
def x():
    g = torch.Generator().manual_seed(1)
    x = torch.randn(T, seqfeat.N_CHANNELS, generator=g)
    x[L:] = 0.0  # 패딩 규약: build_sequences는 유효 길이 밖을 0으로 둔다
    return x


@pytest.fixture(scope="module")
def attrs(model, x):
    return trade_attributions(model, x, L)


def test_shape(attrs):
    assert attrs.shape == (L, N_TARGETS, T, seqfeat.N_CHANNELS)


def test_causality_no_future_attribution(attrs):
    """거래 t의 점수는 거래 1..t만 조건 — t 이후 시점 기여는 정확히 0."""
    for t in range(L):
        assert torch.all(attrs[t, :, t + 1:, :] == 0.0), f"t={t}에 미래 기여 존재"


def test_padding_has_no_attribution(attrs):
    assert torch.all(attrs[:, :, L:, :] == 0.0)


def test_completeness(model, x):
    """기여도 총합 ≈ 로짓(입력) − 로짓(기준선). 스텝을 늘리면 수렴해야 한다."""
    attrs = trade_attributions(model, x, L, steps=256)
    with torch.no_grad():
        logits = model(x.unsqueeze(0), torch.tensor([L]))[0]          # [T, 4]
        base = model(torch.zeros_like(x).unsqueeze(0), torch.tensor([L]))[0]
    want = logits[:L] - base[:L]                                      # [L, 4]
    got = attrs.sum(dim=(2, 3))                                       # [L, 4]
    torch.testing.assert_close(got, want, rtol=0.05, atol=0.01)


def test_batch_cap_invariance(model, x, attrs):
    """배치를 잘게 쪼개도(타깃 1개씩) 값이 같다 — 청킹은 순수 구현 세부."""
    small = trade_attributions(model, x, L, batch_cap=1)
    torch.testing.assert_close(small, attrs)


def test_deterministic(model, x, attrs):
    again = trade_attributions(model, x, L)
    assert torch.equal(again, attrs)


def test_evidence_summary_contract():
    """요약 규약: own/context 분해, |기여| 상위 정렬, 부호 유지."""
    C = seqfeat.N_CHANNELS
    attr = torch.zeros(4, C)
    attr[0, 0] = 0.5                      # 과거 문맥 (t=2 기준)
    attr[1, 1] = -0.2                     # 과거 문맥
    attr[2, 0] = 0.42                     # 자기 시점: side
    attr[2, 9] = -0.30                    # 자기 시점: hld (음수 — 점수를 깎음)
    attr[2, 2] = 0.05                     # 자기 시점: gap
    out = evidence_summary(attr, t=2, top_k=2)

    assert out["own_total"] == pytest.approx(0.42 - 0.30 + 0.05)
    assert out["context_total"] == pytest.approx(0.5 - 0.2)
    # |기여| 상위 2개 = side(0.42), hld(-0.30) — 부호 그대로
    assert [f["feature"] for f in out["features"]] == ["side", "hld"]
    assert out["features"][1]["attribution"] == -0.3
    assert all(f["name"] == FEATURE_NAMES[f["feature"]] for f in out["features"])


def test_evidence_summary_first_trade_has_no_context():
    attr = torch.zeros(3, seqfeat.N_CHANNELS)
    attr[0, 3] = 0.7
    out = evidence_summary(attr, t=0, top_k=3)
    assert out["context_total"] == 0.0
    assert out["own_total"] == pytest.approx(0.7)


def test_channels_match_seqfeat_layout():
    """채널 표(이름 매핑)가 seqfeat의 실제 시퀀스 컬럼 순서와 일치."""
    assert CHANNELS == (seqfeat.BASE_FEATURES
                        + [f"m_{f}" for f in seqfeat.MASKED_FEATURES])
    assert len(CHANNELS) == seqfeat.N_CHANNELS
    assert set(FEATURE_NAMES) == set(CHANNELS)
