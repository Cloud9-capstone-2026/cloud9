"""
태거 하이퍼파라미터 스윕 — 검증 손실(val_bce)로만 선발, 평가 시드는 봉인 유지.

실행: python -m ml.sweep_tagger  (레포 최상위, CPU ~1시간)

그리드: hidden {64,128} × layers {1,2} × dropout {0,0.2} (lr 1e-3) 8조합
        + 저학습률 확인 2조합(최소·최대 용량 × lr 3e-4) = 총 10.
데이터는 1회만 적재해 재사용. 선발 기준은 val_bce — 평가 시드(101/102)는 최종
확정 모델의 1회 평가에만 쓴다(선발에 쓰면 평가가 오염됨).
결과는 표로 출력만 하고 아티팩트는 저장하지 않는다 — 최적 조합 확정 후
train_tagger.main(그 조합)으로 재학습·평가·저장한다.
"""

import time

from .train_tagger import load_train_tensors, train_config

# (hidden, layers, dropout, lr)
CONFIGS = [
    (64, 1, 0.0, 1e-3),   # 현행 기본값 (기준점)
    (64, 1, 0.2, 1e-3),
    (64, 2, 0.0, 1e-3),
    (64, 2, 0.2, 1e-3),
    (128, 1, 0.0, 1e-3),
    (128, 1, 0.2, 1e-3),
    (128, 2, 0.0, 1e-3),
    (128, 2, 0.2, 1e-3),
    (64, 1, 0.0, 3e-4),
    (128, 2, 0.2, 3e-4),
]


def main():
    print("학습 데이터 적재 (1회)...", flush=True)
    data = load_train_tensors()
    results = []
    for i, (h, l, d, lr) in enumerate(CONFIGS, 1):
        t0 = time.time()
        best, _state, ep = train_config(data, h, l, d, lr, verbose=False)
        dt = time.time() - t0
        results.append((best, h, l, d, lr, ep, dt))
        print(f"[{i:2d}/{len(CONFIGS)}] hidden={h:3d} layers={l} drop={d} lr={lr:.0e}"
              f"  val_bce={best:.4f}  (best epoch {ep}, {dt / 60:.1f}분)", flush=True)

    print("\n=== val_bce 순위 ===")
    for best, h, l, d, lr, ep, _dt in sorted(results):
        print(f"  {best:.4f}  hidden={h:3d} layers={l} drop={d} lr={lr:.0e} (ep {ep})")
    top = sorted(results)[0]
    print(f"\n최적: hidden={top[1]} layers={top[2]} drop={top[3]} lr={top[4]:.0e}"
          f" — train_tagger.main(이 조합)으로 재학습·평가·저장할 것")


if __name__ == "__main__":
    main()
