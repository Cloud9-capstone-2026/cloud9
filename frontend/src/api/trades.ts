import { api } from './client';

export interface UploadResponse {
  upload_id: number;
  job_id: number;
  status: string;
  message: string;
}

export interface JobStatus {
  job_id: number;
  status: 'pending' | 'running' | 'done' | 'failed';
  upload_id?: number;
  message?: string;
  error_type?: string;
}

export interface UploadHistoryItem {
  id: number;
  file_name: string;
  row_count: number | null;
  status: string;
  uploaded_at: string;
}

export interface TradeRaw {
  id: number;
  user_id: number | null;
  upload_id: number | null;
  거래일자: string;
  종목명: string;
  거래구분: string;
  거래수량: number;
  거래단가: number;
  거래금액: number;
  수수료: number;
  거래세: number;
  정산금액: number;
}

export async function uploadTrades(fileUri: string, fileName: string, mimeType: string) {
  const formData = new FormData();
  // React Native의 FormData는 웹 File/Blob이 아니라 {uri, name, type} 객체를 받는다.
  formData.append('file', { uri: fileUri, name: fileName, type: mimeType || 'application/octet-stream' } as any);
  const { data } = await api.post<UploadResponse>('/trades/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
}

export async function getJobStatus(jobId: number) {
  const { data } = await api.get<JobStatus>(`/jobs/${jobId}`);
  return data;
}

export async function getUploads(limit = 50, offset = 0) {
  const { data } = await api.get<UploadHistoryItem[]>('/trades/uploads', { params: { limit, offset } });
  return data;
}

export async function getTrades(limit = 50, offset = 0) {
  const { data } = await api.get<TradeRaw[]>('/trades/', { params: { limit, offset } });
  return data;
}
