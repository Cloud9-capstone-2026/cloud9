"""
XAI — Integrated Gradients (IG): layer3 GRU의 편향 점수를 거래(시점)별 기여도로 분해.

태초 문법("네가 한 이 거래는 ~편향 때문일 수도")의 1단계 구현: 계좌 수준 편향
점수를 만든 근거를 시퀀스의 각 거래에 귀속시킨다. captum 없이 직접 구현 —
IG는 (입력 − 기준선) × 경로 위 평균 그래디언트라 수십 줄로 충분하고,
백엔드 의존성을 늘리지 않는다.

기준선(baseline) = 영벡터: seqfeat 정규화 후 0은 "모든 피처가 학습 분포의
평균이고 시장 컨텍스트는 전부 결측"인 무정보 거래에 해당한다 — 즉 기여도는
"이 거래가 무정보 거래 대비 편향 점수를 얼마나 밀었나"로 읽는다.
"""

import torch

IG_STEPS = 32  # 경로 적분 근사 스텝 (완전성 오차 대비 계산량 절충)


def integrated_gradients(model, x, length: int, n_targets: int,
                         steps: int = IG_STEPS) -> torch.Tensor:
    """단일 계좌 시퀀스의 타깃별·시점별 IG 기여도.

    x: [T, C] (seqfeat 정규화 완료 텐서), length: 유효 길이(패딩 제외).
    반환: [n_targets, T] — 입력 채널 합산 기여도. 패딩 시점은 0.
    """
    model.eval()
    x0 = x.unsqueeze(0)                      # [1, T, C]
    baseline = torch.zeros_like(x0)
    alphas = torch.linspace(1.0 / steps, 1.0, steps).view(-1, 1, 1)
    path = (baseline + alphas * (x0 - baseline)).detach().requires_grad_(True)
    lengths = torch.full((steps,), int(length), dtype=torch.long)

    out = model(path, lengths)               # [steps, n_targets]
    attrs = []
    for j in range(n_targets):
        grads = torch.autograd.grad(
            out[:, j].sum(), path, retain_graph=(j < n_targets - 1)
        )[0]                                  # [steps, T, C]
        avg_grad = grads.mean(dim=0)          # [T, C]
        attrs.append(((x0[0] - baseline[0]) * avg_grad).sum(dim=1))  # [T]
    return torch.stack(attrs).detach()        # [n_targets, T]
