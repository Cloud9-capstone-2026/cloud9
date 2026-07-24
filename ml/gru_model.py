"""
GRU 멀티태스크 회귀 모델 정의 — 학습(ml.train_gru)과 추론(backend.models.layer3) 공유.

이 모듈만 따로 둔 이유: 추론(backend)이 학습 스크립트의 무거운 의존성(sklearn·scipy)
없이 모델 구조만 import할 수 있게 하기 위함.
"""

from torch import nn
from torch.nn.utils.rnn import pack_padded_sequence, pad_packed_sequence


class GRUTagger(nn.Module):
    """이벤트 시퀀스 [B, T, C] → 각 시점(거래)별 편향 귀속 로짓 [B, T, n_targets].

    2단계 시퀀스 태깅: 타깃은 생성기의 거래별 인과 귀속 확률(trade_labels).
    단방향 GRU라 시점 t의 출력은 거래 1..t 이력만 조건으로 한다 — "그 시점까지의
    이전 거래들을 고려해 이 거래를 판단"하는 인과 방향이 구조적으로 보장된다.
    출력은 로짓 — 확률은 sigmoid, 학습 손실은 BCEWithLogits(패딩 마스크 적용).
    """

    def __init__(self, n_features: int, hidden: int, layers: int, n_targets: int):
        super().__init__()
        self.gru = nn.GRU(n_features, hidden, num_layers=layers, batch_first=True)
        self.head = nn.Sequential(
            nn.Linear(hidden, 64), nn.ReLU(), nn.Linear(64, n_targets)
        )

    def forward(self, x, lengths):
        packed = pack_padded_sequence(
            x, lengths.cpu(), batch_first=True, enforce_sorted=False
        )
        out, _ = self.gru(packed)
        out, _ = pad_packed_sequence(out, batch_first=True, total_length=x.shape[1])
        return self.head(out)  # [B, T, n_targets] 로짓


class GRURegressor(nn.Module):
    """이벤트 시퀀스 [B, T, C] → 4개 편향 파라미터 회귀.

    가변 길이는 pack_padded_sequence로 처리 — 패딩 구간은 GRU 연산에서 제외되므로
    별도 마스크 없이 마지막 유효 hidden state가 계좌 표현이 된다.
    """

    def __init__(self, n_features: int, hidden: int, layers: int, n_targets: int):
        super().__init__()
        self.gru = nn.GRU(n_features, hidden, num_layers=layers, batch_first=True)
        self.head = nn.Sequential(
            nn.Linear(hidden, 64), nn.ReLU(), nn.Linear(64, n_targets)
        )

    def forward(self, x, lengths):
        packed = pack_padded_sequence(
            x, lengths.cpu(), batch_first=True, enforce_sorted=False
        )
        _, h = self.gru(packed)  # h: [layers, B, hidden]
        return self.head(h[-1])
