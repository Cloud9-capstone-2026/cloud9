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
}

export interface AnalysisResult {
  id: number;
  user_id: number;
  upload_id: number | null;
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
