import { api } from './client';
import type { BiasKey } from '../theme/tokens';

export interface SurveyAnswerInput {
  question_id: string;
  value: number;
}

export interface SurveyAxisScore {
  raw: number;
  normalized: number;
  level: 'high' | 'low';
}

export interface SurveyResult {
  result_id: number;
  scores: Record<BiasKey, SurveyAxisScore>;
  type_code: string;
  created_at: string;
}

export async function submitSurvey(answers: SurveyAnswerInput[]) {
  const { data } = await api.post<SurveyResult>('/survey/submit', { answers });
  return data;
}

export async function getLatestSurvey() {
  const { data } = await api.get<SurveyResult>('/survey/latest');
  return data;
}

export async function getSurveyHistory(limit = 20) {
  const { data } = await api.get<SurveyResult[]>('/survey/history', { params: { limit } });
  return data;
}
