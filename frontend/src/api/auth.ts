import { api } from './client';

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface UserProfile {
  id: number;
  email: string | null;
  name: string;
  provider: string | null;
  email_verified: boolean;
  agreed_terms: boolean;
  created_at: string | null;
}

export async function signup(params: { email: string; password: string; name: string; agreedTerms: boolean }) {
  const { data } = await api.post<TokenResponse>('/auth/signup', {
    email: params.email,
    password: params.password,
    name: params.name,
    agreed_terms: params.agreedTerms,
  });
  return data;
}

// /auth/login만 OAuth2PasswordRequestForm(application/x-www-form-urlencoded, 필드명 username/password)을 씀 —
// 다른 모든 엔드포인트는 JSON.
export async function login(email: string, password: string) {
  const body = new URLSearchParams();
  body.append('username', email);
  body.append('password', password);
  const { data } = await api.post<TokenResponse>('/auth/login', body.toString(), {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  });
  return data;
}

export async function verifyEmail(email: string, code: string) {
  await api.post('/auth/verify-email', { email, code });
}

export async function resendVerification(email: string) {
  await api.post('/auth/verify-email/resend', { email });
}

export async function socialLogin(provider: string, token: string) {
  const { data } = await api.post<TokenResponse>(`/auth/social/${provider}`, { token });
  return data;
}

export async function passwordResetRequest(email: string) {
  await api.post('/auth/password-reset/request', { email });
}

export async function passwordResetConfirm(email: string, code: string, newPassword: string) {
  await api.post('/auth/password-reset/confirm', { email, code, new_password: newPassword });
}

export async function getMe() {
  const { data } = await api.get<UserProfile>('/auth/me');
  return data;
}

export async function updateProfile(name: string) {
  const { data } = await api.patch<UserProfile>('/auth/me', { name });
  return data;
}

export async function changePassword(currentPassword: string, newPassword: string) {
  // 현재 비밀번호가 틀려도 401이라, 전역 "토큰 무효 → 강제 로그아웃" 처리 대상에서 제외해야 함.
  await api.put(
    '/auth/me/password',
    { current_password: currentPassword, new_password: newPassword },
    { skipAuthErrorHandling: true }
  );
}

export async function withdraw() {
  await api.post('/auth/withdraw');
}
