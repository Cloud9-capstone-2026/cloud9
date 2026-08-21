"""
실계좌 분포 점검 v2 — sim-to-real 이탈 감지 + 딥러닝 판정 제외.

모델은 합성 데이터로 학습됐다. 실계좌의 행동 지표가 학습 데이터의 분포 범위를
크게 벗어나면(예: 학습에 없던 초고회전 계좌) 그 계좌에 대한 딥러닝 판정은
배운 적 없는 영역에 대한 외삽이라 신뢰도가 낮다.

v2 (2026-08-18 회의 + 8-21 민감도 결정): 이탈 지표가 발동 기준 개수 이상이면
deep_excluded=True — detect.py가 그 계좌의 3계층 채점을 생략하고 규칙+통계
2계층으로만 판정한다(프론트는 주의 문구 표시). 기준 미만 이탈은 v1처럼 기록만.

기준 분포: ml/artifacts/distribution_ref.json — 학습 데이터(확장 5시드,
계좌 단위)의 지표별 분위수. 모델과 같은 Release 번들로 배포되므로
"이 모델이 배운 분포"와 항상 짝이 맞는다.

판정 규칙: 지표값이 [p1, p99] 밖이면 그 지표를 이탈로 기록.
  status = "ok"           전 지표 범위 안
         | "out_of_range" 1개 이상 이탈 (out_of_range에 상세)
         | "unavailable"  계좌 지표 없음(산출 실패) 또는 기준 파일 부재
  deep_excluded = 이탈 지표 수 >= CANARY_DIST_TRIGGER(기본 2) — 모든 상태에서
  항상 존재(unavailable이면 False). 프론트는 이 필드만 보면 되고, status·
  out_of_range 상세는 내부 진단·민감도 튜닝 재료다.

발동 기준을 2개로 시작하는 이유: 기준선(상하위 1%)이 민감해 정상 계좌도 지표
하나쯤은 걸릴 수 있고, 진짜 분포 밖 계좌는 지표들이 상관돼 있어 여러 개가
같이 이탈한다(초단타 → 회전율·보유기간·거래수 동시). 실사용 데이터가 쌓이면
환경변수로 조정한다.
"""

import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# layer3와 같은 아티팩트 위치 규약 (환경변수 우선) — layer3를 import하지 않는
# 이유: 이 모듈은 torch 없는 환경에서도 살아야 한다
_REPO_ROOT = Path(__file__).resolve().parents[2]
_ART_DIR = Path(os.environ.get("CANARY_MODEL_DIR", _REPO_ROOT / "ml" / "artifacts"))


def _load_ref() -> dict | None:
    path = _ART_DIR / "distribution_ref.json"
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as fp:
            return json.load(fp)
    except Exception as e:  # noqa: BLE001 — 손상 파일은 부재와 동일 취급
        logger.warning("distribution_ref.json 손상 — 분포 점검 생략: %r", e)
        return None


def check_distribution(account_metrics: dict | None) -> dict:
    """계좌 지표를 학습 분포 [p1, p99]와 대조.

    account_metrics: layer3가 산출한 지표 dict (실패 시 None). 값이 None인
    지표(예: 매도만 있어 보유기간 미정의)는 점검에서 제외하고 checked에서 뺀다.
    """
    ref = _load_ref()
    if not account_metrics or ref is None:
        return {"status": "unavailable", "deep_excluded": False}

    out_of_range = {}
    checked = []
    for name, spec in ref.get("metrics", {}).items():
        value = account_metrics.get(name)
        if value is None:
            continue
        q = spec["quantiles"]
        p1, p99 = q[0], q[-1]
        checked.append(name)
        if not (p1 <= value <= p99):
            out_of_range[name] = {
                "value": round(float(value), 6), "ref_p1": p1, "ref_p99": p99}

    # 발동 기준은 호출 시점에 읽음 — 서버 재시작만으로 조정 가능
    n_trigger = int(os.environ.get("CANARY_DIST_TRIGGER", "2"))
    return {
        "status": "out_of_range" if out_of_range else "ok",
        "checked": checked,
        "out_of_range": out_of_range,
        "deep_excluded": len(out_of_range) >= n_trigger,
    }
