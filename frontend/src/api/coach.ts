import { api } from './client';
import type { BiasKey } from '../theme/tokens';

export interface AccountBiasScore {
  score: number | null;
  n_trades: number;
  side: '매수' | '매도';
}

export interface AccountBiasScoresResponse {
  scores: Record<BiasKey, AccountBiasScore>;
}

export async function getAccountBiasScores() {
  const { data } = await api.get<AccountBiasScoresResponse>('/coach/scores');
  return data;
}
