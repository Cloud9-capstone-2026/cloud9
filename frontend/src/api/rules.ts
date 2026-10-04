import { api } from './client';

export interface RuleApiItem {
  rule_id: string;
  label: string;
  param_unit: string | null;
  default_param: number | null;
  default_on: boolean;
  enabled: boolean;
  param: number | null;
  updated_at: string | null;
}

export async function getRules() {
  const { data } = await api.get<RuleApiItem[]>('/rules/');
  return data;
}

// source: 'recommendation' = 규칙 조언 카드에서 켠 경우, 생략 시 서버 기본값 'manual'
// (설정 화면에서 직접 켠 경우) — 이후 효과 측정에서 "추천으로 켠 규칙인지" 구분하는 용도.
export async function setRule(ruleId: string, enabled: boolean, param: number | null, source?: 'manual' | 'recommendation') {
  const { data } = await api.put<RuleApiItem>(`/rules/${ruleId}`, { enabled, param, ...(source ? { source } : {}) });
  return data;
}

export interface RuleEffectUploadRow {
  upload_id: number;
  file_name: string;
  uploaded_at: string;
  n_trades: number;
  violations: number;
  violation_rate: number | null;
  after_adoption: boolean;
}

export interface RuleEffectSummary {
  n_uploads: number;
  n_trades: number;
  violations: number;
  violation_rate: number | null;
}

export interface RuleEffectResponse {
  rule_id: string;
  label: string;
  param: number | null;
  param_unit: string | null;
  currently_enabled: boolean;
  adopted_at: string | null;
  adopted_source: string | null;
  uploads: RuleEffectUploadRow[];
  summary: {
    before: RuleEffectSummary;
    after: RuleEffectSummary;
    comparable: boolean;
  };
}

// param: 미리보기할 파라미터(아직 안 켠 규칙이면 그 파라미터 전부 before 버킷에 잡힘).
// 생략하면 서버가 사용자 저장값 → 템플릿 기본값 순으로 적용.
export async function getRuleEffect(ruleId: string, param?: number | null) {
  const { data } = await api.get<RuleEffectResponse>(`/rules/${ruleId}/effect`, {
    params: param != null ? { param } : undefined,
  });
  return data;
}
