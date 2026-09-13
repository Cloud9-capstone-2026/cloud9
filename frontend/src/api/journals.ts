import { api } from './client';

export interface JournalApiItem {
  id: number;
  trade_id: number;
  stock: string;
  date: string;
  type: string;
  emotion: string;
  memo: string;
  reason: string;
  review: string;
  created_at: string;
  updated_at: string;
}

export async function getJournals(limit = 100, offset = 0) {
  const { data } = await api.get<JournalApiItem[]>('/journals/', { params: { limit, offset } });
  return data;
}

export async function createJournal(tradeId: number, emotion: string, reason: string, review: string) {
  const { data } = await api.post<JournalApiItem>('/journals/', { trade_id: tradeId, emotion, reason, review });
  return data;
}

export async function updateJournal(journalId: number, emotion: string, reason: string, review: string) {
  const { data } = await api.put<JournalApiItem>(`/journals/${journalId}`, { emotion, reason, review });
  return data;
}

export async function deleteJournal(journalId: number) {
  const { data } = await api.delete<{ id: number; deleted: boolean }>(`/journals/${journalId}`);
  return data;
}
