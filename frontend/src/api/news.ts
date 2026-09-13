import { api } from './client';
import type { DartNews } from '../data/types';

export async function getNews(limit = 20, offset = 0, period?: string) {
  const { data } = await api.get<DartNews[]>('/news/', { params: { limit, offset, period } });
  return data;
}

export async function getRelatedNews(tradeId: number, limit = 3) {
  const { data } = await api.get<DartNews[]>('/news/related', { params: { trade_id: tradeId, limit } });
  return data;
}
