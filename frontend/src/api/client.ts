import axios from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';

declare module 'axios' {
  export interface AxiosRequestConfig {
    // true면 이 요청의 401을 "토큰 무효" 전역 처리(강제 로그아웃) 대상에서 제외.
    skipAuthErrorHandling?: boolean;
  }
}

// 로그인 성공 시 발급받는 JWT access_token 저장 키.
// 백엔드는 refresh token을 발급하지 않음 — 만료되면 재로그인이 유일한 복구 경로.
const TOKEN_STORAGE_KEY = '@canary/token';

export async function getToken(): Promise<string | null> {
  return AsyncStorage.getItem(TOKEN_STORAGE_KEY);
}

export async function setToken(token: string): Promise<void> {
  await AsyncStorage.setItem(TOKEN_STORAGE_KEY, token);
}

export async function clearToken(): Promise<void> {
  await AsyncStorage.removeItem(TOKEN_STORAGE_KEY);
}

// 401(토큰 만료/무효) 응답을 받았을 때 AppState가 로그아웃 처리를 하도록 등록하는 콜백.
// client.ts가 AppState.tsx를 import하면 순환참조가 생기므로, AppState 쪽에서
// 앱 시작 시 이 콜백을 등록하는 방식으로 역방향 의존을 피한다.
let unauthorizedHandler: (() => void) | null = null;
export function setUnauthorizedHandler(handler: () => void) {
  unauthorizedHandler = handler;
}

export const api = axios.create({
  baseURL: process.env.EXPO_PUBLIC_API_URL,
  timeout: 15000,
});

api.interceptors.request.use(async (config) => {
  const token = await getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    // 401이 전부 "토큰 무효/만료"는 아님 — PUT /auth/me/password는 현재
    // 비밀번호가 틀렸을 때도 401을 준다. 그런 요청은 호출부에서
    // skipAuthErrorHandling: true를 넘겨 전역 강제 로그아웃을 피한다.
    if (error.response?.status === 401 && !error.config?.skipAuthErrorHandling) {
      await clearToken();
      unauthorizedHandler?.();
    }
    return Promise.reject(error);
  }
);
