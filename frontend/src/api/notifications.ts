import { api } from './client';

export type NotifApiType = 'upload' | 'uploadFail' | 'analysis' | 'analyzeFail';

export interface NotificationApiItem {
  id: number;
  type: NotifApiType;
  file_name: string | null;
  trade_count: number | null;
  job_id: number | null;
  upload_id: number | null;
  is_read: boolean;
  created_at: string;
}

export interface NotificationsResponse {
  notifications: NotificationApiItem[];
  unread_count: number;
}

export async function getNotifications(limit = 100, offset = 0) {
  const { data } = await api.get<NotificationsResponse>('/notifications/', { params: { limit, offset } });
  return data;
}

export async function markNotificationRead(id: number) {
  const { data } = await api.post<NotificationApiItem>(`/notifications/${id}/read`);
  return data;
}
