import { api } from './client';
import type { BiasKey } from '../theme/tokens';

export interface AnalysisEvidenceFeature {
  feature: string;
  attribution: number;
}

export interface AnalysisEvidenceAxis {
  trade_share: number;
  context_share: number;
  features: AnalysisEvidenceFeature[];
}

// 규칙 조언(코치) — 이 거래의 편향 점수가 3계층 임계값을 넘었을 때, 그 편향을
// 줄이는 데 도움되는 1계층 규칙을 켜보라는 제안. 매핑된 규칙이 없거나(복권형·군집),
// 이미 켜져 있는 규칙이면 애초에 비어있는 배열로 온다(pipeline/coach.py::rule_advice).
export interface RuleAdviceItem {
  bias: BiasKey;
  rule_id: string;
  label: string;
  suggested_param: number;
  param_unit: string | null;
}

export interface AnalysisDetail {
  날짜: string;
  종목명: string;
  verdict: '정상' | '경고' | '이상';
  flags: { rule?: boolean; stat?: boolean; deep?: boolean };
  layers_available: number;
  triggered_rules: string[] | null;
  mahalanobis: number | null;
  top_bias: BiasKey | null;
  top_bias_명: string | null;
  bias_scores: Record<BiasKey, number> | null;
  evidence: Record<BiasKey, AnalysisEvidenceAxis> | null;
  deep_excluded: boolean;
  rule_advice: RuleAdviceItem[];
  advice_disclaimer: string | null;
}

export interface AnalysisResult {
  id: number;
  user_id: number;
  upload_id: number | null;
  trade_id: number | null;
  rule_score: number | null;
  stat_score: number | null;
  deep_score: number | null;
  is_anomaly: boolean;
  detail: AnalysisDetail;
  analyzed_at: string;
}

export async function getAnalysis(limit = 50, offset = 0) {
  const { data } = await api.get<AnalysisResult[]>('/analysis/', { params: { limit, offset } });
  return data;
}
