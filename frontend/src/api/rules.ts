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

export async function setRule(ruleId: string, enabled: boolean, param: number | null) {
  const { data } = await api.put<RuleApiItem>(`/rules/${ruleId}`, { enabled, param });
  return data;
}
