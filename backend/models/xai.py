"""
XAI — Integrated Gradients (IG): GRU 태거의 거래별 편향 점수를 입력 기여도로 분해.

목적: "GRU가 이 거래에 편향 4종 점수를 왜 이렇게 매겼나" — 타깃은 (거래 t, 편향 j)의
로짓 하나이고, IG가 그 로짓에 대한 [시점 × 채널] 기여도를 내놓는다. 요약은
  - 거래 t 자신의 시점 → 피처별 기여도 (부호 포함 — 점수를 올린/깎은 피처 모두)
  - t 이전 시점 전체 합 → 과거 문맥 기여 총량 (상세 분해 없이 총량만)
의 두 축으로 한다. 단방향 GRU라 t 이후 시점의 기여는 정확히 0 (테스트가 보증).

기준선(baseline) = 영벡터: seqfeat 정규화 후 0은 "모든 피처가 학습 분포의 평균이고
시장 컨텍스트는 전부 결측"인 무정보 거래에 해당한다 — 기여도는 "이 입력이 무정보
거래 대비 로짓을 얼마나 밀었나"(로짓 단위)로 읽는다.

captum 없이 직접 구현 — IG는 (입력 − 기준선) × 경로 위 평균 그래디언트라 수십 줄로
충분하고, 백엔드 의존성을 늘리지 않는다. 경로 적분은 중점 규칙(스텝 중앙의 알파)로
근사한다.
"""

import os
import sys
from pathlib import Path

import torch

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from ml import seqfeat

# 경로 적분 근사 스텝 (완전성 오차 대비 계산량 절충). 서버 CPU가 느려 분석이
# 오래 걸리면 환경변수로 16까지 낮춰 절반으로 줄일 수 있다(정밀도 소폭 희생).
IG_STEPS = int(os.environ.get("CANARY_XAI_STEPS", "32"))
BATCH_CAP = 1024  # 한 순전파에 넣는 (타깃 복사본 × 스텝) 상한 — 메모리 절충

# 시퀀스 채널 순서 = seqfeat.build_sequences의 컬럼 순서 (기본 10 + 결측 마스크 7)
CHANNELS = seqfeat.BASE_FEATURES + [f"m_{f}" for f in seqfeat.MASKED_FEATURES]

_BASE_NAMES = {
    "side": "매수여부",
    "amt": "거래금액",
    "gap": "직전거래간격",
    "abn": "비정상거래량",
    "r1": "전일수익률",
    "r5": "최근5일수익률",
    "lott": "복권성순위",
    "drv": "지수수익률",
    "ras": "매도실현수익률",
    "hld": "보유기간",
}
# 마스크 채널: 값이 아니라 "그 피처가 관측됐는지"가 모델 입력 — 표시명에 명시
FEATURE_NAMES = {**_BASE_NAMES,
                 **{f"m_{f}": f"{_BASE_NAMES[f]}(관측)"
                    for f in seqfeat.MASKED_FEATURES}}


def trade_attributions(model, x: torch.Tensor, length: int,
                       steps: int = IG_STEPS,
                       batch_cap: int = BATCH_CAP,
                       targets: list[int] | None = None) -> torch.Tensor:
    """단일 계좌 시퀀스의 거래 × 편향 IG 기여도.

    x: [T, C] (seqfeat 정규화 완료 텐서), length: 유효 길이 L (패딩 제외).
    targets: 기여도를 계산할 거래 위치 목록 (기본 전체 0..L-1) — 창 분할
    채점에서 창당 필요한 위치만 계산해 총량을 거래 수에 비례시키는 용도.
    반환: [len(targets), n_targets, T, C] — i번째가 targets[i] 거래의 편향별
    입력 기여도. 패딩 시점과 (인과성에 의해) 대상 거래 이후 시점은 0.

    비용 절감 두 가지 (값은 동일 — 테스트가 청킹 불변성으로 보증):
    - 거래별 그래디언트가 서로 섞이지 않도록 거래마다 경로 복사본을 따로 두고,
      복사본들이 배치에서 독립이라는 성질로 backward 1회에 여러 거래를 처리
    - 단방향 GRU의 인과성: 거래 t의 로짓은 t 이후 입력과 무관 → 복사본 길이를
      t+1로 잘라 계산량을 절반 수준으로. 순전파는 편향 4종이 공유하고
      역전파만 타깃별로 수행
    """
    model.eval()
    T, C = x.shape
    L = int(length)
    x = x.detach()

    with torch.no_grad():
        n_targets = model(x.unsqueeze(0), torch.tensor([L])).shape[-1]

    # 중점 규칙: alpha = (i + 0.5) / steps — 기준선이 영벡터라 경로점은 alpha * x
    alphas = ((torch.arange(steps, dtype=x.dtype) + 0.5) / steps).view(-1, 1, 1)
    path_pts = alphas * x                    # [steps, T, C] (전 거래 공유 값)

    ts_all = list(range(L)) if targets is None else [int(t) for t in targets]
    attrs = torch.zeros(len(ts_all), n_targets, T, C, dtype=x.dtype)
    chunk = max(1, batch_cap // steps)       # 한 배치에 담는 거래 수
    for c0 in range(0, len(ts_all), chunk):
        ts = torch.tensor(ts_all[c0:c0 + chunk])
        k = len(ts)
        inp = (path_pts.repeat(k, 1, 1)      # [k*steps, T, C] 거래별 독립 복사본
               .detach().requires_grad_(True))
        sel_t = ts.repeat_interleave(steps)
        out = model(inp, sel_t + 1)          # 길이 t+1 — 이후 시점은 계산 생략
        idx = torch.arange(k * steps)
        for j in range(n_targets):
            target = out[idx, sel_t, j].sum()
            grads = torch.autograd.grad(
                target, inp, retain_graph=(j < n_targets - 1)
            )[0]                                               # [k*steps, T, C]
            avg_grad = grads.view(k, steps, T, C).mean(dim=1)  # [k, T, C]
            attrs[c0:c0 + k, j] = x * avg_grad  # (입력 − 기준선) = x
    return attrs.detach()


def evidence_summary(attr_tj: torch.Tensor, t: int,
                     top_k: int | None = None) -> dict:
    """한 (거래 t, 편향 j) 기여도 [T, C] → 현재 거래/과거 문맥 요약.

    반환 (값은 전부 로짓 단위, 부호 유지):
      own_total      거래 t 자신의 전 채널 기여 합
      context_total  t 이전 시점 전체 기여 합
      features       거래 t 자신의 채널별 기여, |기여| 내림차순 —
                     [{"feature": 채널 코드, "name": 표시명, "attribution": 값}]
                     기본은 전 채널, top_k 지정 시 상위 top_k만
    """
    own = attr_tj[t]                             # [C]
    order = own.abs().argsort(descending=True)
    if top_k is not None:
        order = order[:top_k]
    return {
        "own_total": round(float(own.sum()), 4),
        "context_total": round(float(attr_tj[:t].sum()), 4),
        "features": [{
            "feature": CHANNELS[i],
            "name": FEATURE_NAMES[CHANNELS[i]],
            "attribution": round(float(own[i]), 4),
        } for i in order.tolist()],
    }
