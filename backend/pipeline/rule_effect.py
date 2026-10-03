"""
규칙 효과 측정 — 진단→규칙 추천→재업로드 닫힌 고리의 마지막 단계.

"이 규칙을 켠 뒤 위반이 줄었나"를 업로드별 위반율로 보여준다.

저장된 판정을 쓰지 않는 이유: 1계층은 켜진 규칙만 판정하고 소급하지 않는다.
그래서 규칙을 켜기 전 업로드에는 그 규칙 위반이 항상 0으로 저장돼 있고,
저장값으로 전후를 비교하면 "켰더니 위반이 0 → N으로 늘었다"는 거꾸로 된
결과가 나온다. 대신 지금 기준(같은 규칙·같은 파라미터)을 모든 업로드에 똑같이
다시 적용해 같은 자로 전후를 잰다.

재계산은 실제 분석(detect.run_pipeline_from_db)과 같은 방식으로 한다:
업로드 k의 판정 = [k보다 앞선 업로드 거래(날짜 정렬)] + [k의 거래(날짜 정렬)]를
전체 이력으로 두고 k의 거래만 판정. 손실 후 재진입처럼 과거 거래가 문맥인
규칙도 실제 분석과 같은 결과가 나온다. 조회 시 계산만 하고 저장하지 않는다.

비교 단위는 건수가 아닌 위반율(위반 거래 / 거래 수) — 업로드마다 거래 수가
달라서 건수로는 비교가 안 된다.

시각 비교(분석 시작 vs 규칙 켠 시각)는 EC2·RDS 둘 다 UTC라는 전제다
(job.started_at은 서버 datetime.now(), 이력 created_at은 DB now()).
"""

from datetime import datetime

import pandas as pd

from models.rule_based import run_rule_based
from models.rule_based.templates import TEMPLATES
from orm import AnalysisJob, CsvUpload, RuleChangeLog, Trade, UserRule
from pipeline.detect import _trades_to_df


class EffectParamError(ValueError):
    """금액 한도류처럼 추천값이 없는데 파라미터도 없는 경우."""


def adoption_point(logs) -> tuple[datetime | None, str | None]:
    """변경 이력(오래된 순) → 현재 켜져 있는 구간이 시작된 시각과 출처.

    꺼진 상태에서 켜진 순간이 시작점이다. 켜진 채로 파라미터만 바꾼 건
    새 시작이 아니다. 지금 꺼져 있거나 이력이 없으면 (None, None) —
    이력은 2026-10-03부터 쌓여서 그 전에 켠 규칙은 시작점을 알 수 없다.
    user_rules.updated_at으로 대신하지 않는다: 파라미터만 바꿔도 갱신돼 켠
    날짜가 아닐 수 있고, 틀린 기준점으로 나눈 전후 비교는 없느니만 못하다."""
    start, source, on = None, None, False
    for log in logs:
        if log.enabled and not on:
            start, source = log.created_at, log.source
        elif not log.enabled:
            start, source = None, None
        on = log.enabled
    return start, source


def _violations_per_upload(rule_id: str, param, trades_by_upload: dict) -> dict:
    """{upload_id: [Trade]} (upload_id 오름차순) → {upload_id: 위반 거래 수}."""
    label = TEMPLATES[rule_id].표시명
    ruleset = [(rule_id, param)]
    out = {}
    prev = []
    for upload_id, trades in trades_by_upload.items():
        new_df = _trades_to_df(trades).drop(columns="_tid")
        base_df = _trades_to_df(prev).drop(columns="_tid")
        if len(base_df):
            history = pd.concat([base_df, new_df], ignore_index=True)
        else:
            history = new_df
        positions = range(len(base_df), len(history))
        result = run_rule_based(history, positions, ruleset)
        out[upload_id] = sum(
            1 for r in result["trade_results"] if label in r["triggered_rules"])
        prev = prev + trades
    return out


def compute_rule_effect(db, user_id: int, rule_id: str,
                        param_override: float | None = None) -> dict:
    """규칙 하나의 업로드별 위반율 + 켠 시점 기준 전후 요약.

    적용 파라미터 우선순위: param_override(미리보기) > 사용자 설정값 >
    템플릿 추천값. 셋 다 없으면(금액 한도류 미설정) EffectParamError.
    파라미터가 없는 규칙(당일 왕복매매)은 None 그대로 쓴다."""
    template = TEMPLATES[rule_id]
    user_rule = (db.query(UserRule)
                 .filter(UserRule.user_id == user_id, UserRule.rule_id == rule_id)
                 .first())
    if param_override is not None:
        param = param_override
    elif user_rule is not None and user_rule.param is not None:
        param = user_rule.param
    else:
        param = template.default_param
    if param is None and template.param_unit is not None:
        raise EffectParamError(
            f"{rule_id}는 파라미터가 필요합니다 (단위: {template.param_unit})")

    logs = (db.query(RuleChangeLog)
            .filter(RuleChangeLog.user_id == user_id,
                    RuleChangeLog.rule_id == rule_id)
            .order_by(RuleChangeLog.id).all())
    adopted_at, adopted_source = adoption_point(logs)

    # 분석이 끝난 업로드만 — 실패한 업로드는 거래가 지워져 있다.
    jobs = (db.query(AnalysisJob, CsvUpload)
            .join(CsvUpload, CsvUpload.id == AnalysisJob.upload_id)
            .filter(CsvUpload.user_id == user_id, AnalysisJob.status == "done")
            .order_by(AnalysisJob.upload_id).all())
    trades = (db.query(Trade)
              .filter(Trade.user_id == user_id,
                      Trade.upload_id.in_([j.upload_id for j, _u in jobs]))
              .order_by(Trade.upload_id, Trade.id).all()) if jobs else []
    trades_by_upload = {j.upload_id: [] for j, _u in jobs}
    for t in trades:
        trades_by_upload[t.upload_id].append(t)

    violations = _violations_per_upload(rule_id, param, trades_by_upload)

    uploads = []
    totals = {"before": [0, 0, 0], "after": [0, 0, 0]}  # 업로드 수, 거래, 위반
    for job, upload in jobs:
        n = len(trades_by_upload[job.upload_id])
        v = violations[job.upload_id]
        analyzed_at = job.started_at or upload.uploaded_at
        after = bool(adopted_at and analyzed_at and analyzed_at >= adopted_at)
        uploads.append({
            "upload_id": job.upload_id,
            "file_name": upload.file_name,
            "uploaded_at": upload.uploaded_at,
            "n_trades": n,
            "violations": v,
            "violation_rate": round(v / n, 4) if n else None,
            "after_adoption": after,
        })
        side = totals["after" if after else "before"]
        side[0] += 1
        side[1] += n
        side[2] += v

    def _summary(side):
        n_up, n_tr, n_v = side
        return {"n_uploads": n_up, "n_trades": n_tr, "violations": n_v,
                "violation_rate": round(n_v / n_tr, 4) if n_tr else None}

    return {
        "rule_id": rule_id,
        "label": template.표시명,
        "param": param,
        "param_unit": template.param_unit,
        "currently_enabled": bool(user_rule.enabled) if user_rule is not None
        else template.default_on,
        "adopted_at": adopted_at,
        "adopted_source": adopted_source,
        "uploads": uploads,
        "summary": {
            "before": _summary(totals["before"]),
            "after": _summary(totals["after"]),
            # 전후 둘 다 업로드가 있어야 비교가 성립한다 — 프론트는 false면
            # "비교할 업로드가 아직 없어요" 류로 표시
            "comparable": totals["before"][0] > 0 and totals["after"][0] > 0,
        },
    }