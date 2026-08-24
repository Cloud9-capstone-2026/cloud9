"""
포지션 재생 — 거래 이력만으로 각 거래 시점의 보유 상태를 복원.

CSV에는 거래만 있고 잔고가 없다. "이 매도가 손실이었나", "이 매수가 평단보다
낮나" 같은 손익 기반 규칙(사용자 정의 규칙 템플릿)을 판정하려면 그 시점까지의
매수·매도를 누적해 보유수량·평균단가를 복원해야 한다.

원가 규약은 평균단가법 — 3계층 피처(synthetic_data.features)의 원가 추적과
같은 방식이라 계층 간 손익 부호가 어긋나지 않는다.

상태 저장 없이 매 분석마다 전체 이력을 다시 재생한다(거래 목록 1회 순회 —
수천 건에 수십 ms). 저장된 상태를 증분 갱신하는 방식은 중복 스킵·재시작
정리·재업로드와 얽혀 조용히 어긋나는 버그의 온상이라 채택하지 않는다.

각 행의 결과는 "그 거래를 적용하기 직전" 상태다 — 규칙은 항상 "이 거래를
하려는 순간 상태가 어땠나"를 물으므로.

엣지 정책:
- 이력 밖 잔고 매도(보유량보다 많이/없이 팜 — 업로드 전 보유분): 원가를 알 수
  없으므로 원가미상=True, 실현손익 NaN. 규칙은 이런 매도를 손익 판정에서
  제외한다(모르는 것을 손실로 단정하지 않음). 재생 후 보유는 0으로 리셋.
- 같은 날 여러 거래: 데이터에 나타난 순서대로 재생 (체결 시각이 없으므로).
"""

import numpy as np
import pandas as pd


def replay_positions(df: pd.DataFrame) -> pd.DataFrame:
    """표준 컬럼 거래 이력(날짜·종목명·매매구분·체결수량·체결단가) → 재생 결과.

    반환: df와 같은 인덱스의 DataFrame —
      보유수량_직전   이 거래 직전 그 종목 보유수량
      평균단가_직전   이 거래 직전 그 종목 평균단가 (보유 없으면 NaN)
      최근매수일      이 거래 직전까지 그 종목의 마지막 매수일 (없으면 NaT)
      실현손익        매도 행만: (체결단가 − 평균단가_직전) × 수량. 그 외 NaN
      원가미상        매도 행만: 보유량 부족으로 원가를 모름 (True면 실현손익 NaN)
      최근손실매도일  이 거래 직전까지 그 종목의 마지막 손실 확정 매도일 (없으면 NaT)

    입력 순서와 무관하게 (날짜, 원래 행 순서)로 재생하고 결과는 원래 행에
    정렬해 돌려준다.
    """
    n = len(df)
    nat = np.datetime64("NaT")
    out = {
        "보유수량_직전": np.zeros(n),
        "평균단가_직전": np.full(n, np.nan),
        "최근매수일": np.full(n, nat, dtype="datetime64[ns]"),
        "실현손익": np.full(n, np.nan),
        "원가미상": np.zeros(n, dtype=bool),
        "최근손실매도일": np.full(n, nat, dtype="datetime64[ns]"),
    }
    if n == 0:
        return pd.DataFrame(out, index=df.index)

    dates = pd.to_datetime(df["날짜"]).dt.normalize()
    # 같은 날짜 안에서는 원래 순서 유지 (stable sort)
    order = dates.reset_index(drop=True).sort_values(kind="stable").index

    qty = {}        # 종목 → 보유수량
    avg = {}        # 종목 → 평균단가
    last_buy = {}   # 종목 → 마지막 매수일
    last_loss = {}  # 종목 → 마지막 손실 매도일

    names = df["종목명"].astype(str).to_numpy()
    kinds = df["매매구분"].astype(str).to_numpy()
    qtys = pd.to_numeric(df["체결수량"], errors="coerce").to_numpy(dtype=float)
    prices = pd.to_numeric(df["체결단가"], errors="coerce").to_numpy(dtype=float)
    dts = dates.to_numpy()

    for pos in order:
        name = names[pos]
        q, p, d = qtys[pos], prices[pos], dts[pos]
        held = qty.get(name, 0.0)

        # 거래 적용 "직전" 상태를 기록
        out["보유수량_직전"][pos] = held
        out["평균단가_직전"][pos] = avg.get(name, np.nan)
        out["최근매수일"][pos] = last_buy.get(name, nat)
        out["최근손실매도일"][pos] = last_loss.get(name, nat)

        if "매수" in kinds[pos]:
            new_qty = held + q
            prev_avg = avg.get(name)
            if held > 0 and prev_avg is not None and not np.isnan(prev_avg):
                avg[name] = (held * prev_avg + q * p) / new_qty
            else:
                avg[name] = p
            qty[name] = new_qty
            last_buy[name] = d
        else:  # 매도
            prev_avg = avg.get(name, np.nan)
            if held >= q and not np.isnan(prev_avg):
                pnl = (p - prev_avg) * q
                out["실현손익"][pos] = pnl
                qty[name] = held - q
                if qty[name] == 0:
                    avg.pop(name, None)
                if pnl < 0:
                    last_loss[name] = d
            else:
                # 이력 밖 잔고 — 원가를 모르므로 손익 판정 불가, 보유 리셋
                out["원가미상"][pos] = True
                qty[name] = 0.0
                avg.pop(name, None)

    return pd.DataFrame(out, index=df.index)
