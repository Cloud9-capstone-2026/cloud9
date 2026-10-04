import React, { createContext, useContext, useState, useCallback, useMemo, useRef, useEffect } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { RULES } from '../data/mock';
import type { DartNews } from '../data/types';
import { getToken, setToken, clearToken, setUnauthorizedHandler } from '../api/client';
import * as authApi from '../api/auth';
import * as surveyApi from '../api/survey';
import * as tradesApi from '../api/trades';
import * as analysisApi from '../api/analysis';
import * as rulesApi from '../api/rules';
import * as notificationsApi from '../api/notifications';
import type { NotificationApiItem } from '../api/notifications';
import * as newsApi from '../api/news';
import * as journalsApi from '../api/journals';
import type { JournalApiItem } from '../api/journals';
import * as coachApi from '../api/coach';

export type AuthPhase = 'auth' | 'onboarding' | 'main';

// "로그인 상태 유지" 체크 여부 — 꺼져있으면 앱을 재실행했을 때 토큰이 저장소에
// 남아있어도 자동 로그인을 시도하지 않는다(로그인 시점에 같이 기록).
const KEEP_LOGIN_STORAGE_KEY = '@canary/keepLogin';

// 튜토리얼(온보딩)을 완료했는지 — 계정(user id)별로 저장한다. 이메일이 아니라 id인 이유:
// 탈퇴 후 같은 이메일로 다시 가입하면 이메일은 그대로지만 계정은 새것이라, 이메일을 키로
// 쓰면 새 계정인데도 튜토리얼을 건너뛴다. "로그인 상태 유지"와 별개로 항상 저장됨.
const onboardingDoneKey = (userId: number) => `@canary/onboardingDone:${userId}`;

// 계정 구분 없이 기기 단위로 쓰던 옛 키(2026-10-04 이전). 이게 남아있으면 어떤 계정으로
// 로그인하든 튜토리얼을 건너뛰는 버그가 있어서 계정별 키로 바꿨고, 남은 값은 한 번 지운다.
const LEGACY_ONBOARDING_DONE_STORAGE_KEY = '@canary/onboardingDone';

// 이 기기에 로컬 플래그가 없을 때만(새 기기, 재설치, 저장소 삭제 등) 쓰는 폴백 —
// 서버에 "자가진단 제출 이력"과 "규칙을 직접 저장한 이력"이 둘 다 있으면 온보딩을
// 이미 끝낸 계정으로 간주한다. rules의 updated_at은 사용자가 PUT /rules/{id}를 한
// 번이라도 해야만 값이 생기고(백엔드 routers/rules.py 확인), 아니면 항상 null이라
// "규칙을 직접 설정한 적 있는지"를 신뢰할 수 있게 알려준다. 네트워크 실패 등으로
// 확인 자체가 안 되면 보수적으로 false(온보딩 다시 시킴)를 반환한다.
async function checkServerOnboardingDone(): Promise<boolean> {
  try {
    await surveyApi.getLatestSurvey();
    const rules = await rulesApi.getRules();
    return rules.some((r) => r.updated_at != null);
  } catch {
    return false;
  }
}

// 이 계정이 온보딩을 끝냈는지 — 기기에 저장된 계정별 기록을 먼저 보고, 없으면 서버로 확인한다.
// 로그인·앱 재실행 두 경로가 같은 판단을 하도록 한 군데로 모아둔다.
async function resolveOnboardingDone(userId: number): Promise<boolean> {
  const saved = await AsyncStorage.getItem(onboardingDoneKey(userId)).catch(() => null);
  if (saved === '1') return true;
  const done = await checkServerOnboardingDone();
  if (done) AsyncStorage.setItem(onboardingDoneKey(userId), '1').catch(() => {});
  return done;
}

// 업로드 성공~분석 완료/실패 사이의 "진행 중인 job" 기록. 이 값이 있는 동안은 화면
// 안에서 뒤로가기로 이탈할 수 없고(각 화면의 BackHandler), 앱을 강제종료했다 다시 켜면
// 이 값을 보고 분석 중 화면으로 바로 복귀해 폴링을 재개한다. 분석이 끝나 결과 화면까지
// 도달하면(성공/실패 무관) 지운다.
const PENDING_UPLOAD_STORAGE_KEY = '@canary/pendingUpload';

type RuleOnMap = Record<string, boolean>;
type RuleValMap = Record<string, number>;

interface RuleSnapshot {
  ruleOn: RuleOnMap;
  ruleVal: RuleValMap;
  ruleMoney: RuleValMap;
}

export interface UpFile {
  name: string;
  sizeKB: number | null;
  ext: string;
  uri: string;
  mimeType: string;
  // 웹에서만 채워짐(expo-document-picker가 File 객체를 따로 줌) — 네이티브의
  // {uri,name,type} 방식은 웹 FormData에서 안 먹혀서 업로드 시 이 File을 써야 함.
  webFile?: File;
}

export interface PendingUpload {
  uploadId: number;
  jobId: number;
  fileName: string;
}

interface AppStateValue {
  // 거래일지
  journals: JournalApiItem[];
  refreshJournals: () => Promise<void>;
  saveJournal: (journalId: number, patch: { reason: string; emotion: string; review: string }) => Promise<void>;
  createJournalEntry: (tradeId: number, patch: { reason: string; emotion: string; review: string }) => Promise<void>;
  deleteJournal: (journalId: number) => Promise<void>;
  isJournaled: (tradeId: number) => boolean;

  // 설정 — 알림
  notif: boolean;
  toggleNotif: () => void;

  // 인증 / 온보딩 플로우
  authPhase: AuthPhase;
  authReady: boolean;
  login: (email: string, password: string) => Promise<void>;
  enterMainDirectly: () => void;
  logout: () => Promise<void>;
  completeOnboarding: () => void;
  onboardingDone: boolean;
  keepLogin: boolean;
  setKeepLogin: (v: boolean) => void;

  // 튜토리얼
  tutStep: number;
  setTutStep: (n: number) => void;
  rulesConfirmed: boolean;
  setRulesConfirmed: (v: boolean) => void;

  // 1계층 사용자 정의 규칙
  ruleOn: RuleOnMap;
  ruleVal: RuleValMap;
  ruleMoney: RuleValMap;
  toggleRule: (id: string) => void;
  setRuleVal: (id: string, val: number) => void;
  setRuleMoney: (id: string, val: number) => void;
  ruleSnap: () => void;
  ruleRevert: () => void;
  loadRules: () => Promise<void>;
  saveRules: () => Promise<void>;
  // 규칙 조언 카드의 "규칙 켜기" → 설정 화면 진입 시, 그 규칙을 켜고 제안값을 미리 채워둔다.
  // 저장 시에만 그 규칙 하나를 source:'recommendation'으로 보낸다(나머지는 기본 'manual').
  prefillRuleFromAdvice: (ruleId: string, param: number) => void;
  getRuleEffect: (ruleId: string, param?: number | null) => Promise<import('../api/rules').RuleEffectResponse>;

  // 업로드 플로우
  upFile: UpFile | null;
  setUpFile: (f: UpFile | null) => void;
  uploadFile: (fileUri: string, fileName: string, mimeType: string, webFile?: File) => Promise<import('../api/trades').UploadResponse>;
  pollJobStatus: (jobId: number) => Promise<import('../api/trades').JobStatus>;
  getUploads: (limit?: number, offset?: number) => Promise<import('../api/trades').UploadHistoryItem[]>;
  // 페이지네이션(최대 200/회)을 내부에서 다 순회해서 사용자의 전체 분석 결과를 모아 돌려준다.
  getAllAnalysis: () => Promise<import('../api/analysis').AnalysisResult[]>;
  getAllTrades: () => Promise<import('../api/trades').TradeRaw[]>;
  pendingUpload: PendingUpload | null;
  clearPendingUpload: () => void;

  // 알림 목록
  notifications: NotificationApiItem[];
  refreshNotifications: () => Promise<void>;
  markNotifRead: (id: number) => void;
  markAllNotifRead: () => void;
  unreadNotifCount: number;

  // OS 알림 권한(앱 내 알림 스위치와 별개)
  osNotif: 'granted' | 'denied' | 'unset';
  requestNotifPermission: (allow: boolean) => void;
  notifPermModalOpen: boolean;
  closeNotifPermModal: () => void;

  // 편향 설명 모달 — 어떤 편향(subject)의 설명을 보여줄지
  biasInfo: boolean;
  openBiasInfo: () => void;
  closeBiasInfo: () => void;

  // 프로필
  pfName: string;
  setPfName: (v: string) => void;
  pfEmail: string;
  updateProfileName: (name: string) => Promise<void>;
  changePassword: (currentPassword: string, newPassword: string) => Promise<void>;
  withdrawAccount: () => Promise<void>;

  // 회원가입 / 이메일 인증 / 비밀번호 찾기 — 전부 로그인 안 된 상태에서 호출되는 API라 AppState가 아니어도 되지만,
  // login/logout과 같은 자리에서 관리하는 게 일관적이라 여기 둔다.
  signup: (params: { email: string; password: string; name: string; agreedTerms: boolean }) => Promise<void>;
  verifyEmail: (email: string, code: string) => Promise<void>;
  resendVerification: (email: string) => Promise<void>;
  requestPasswordReset: (email: string) => Promise<void>;
  confirmPasswordReset: (email: string, code: string, newPassword: string) => Promise<void>;
  submitSurvey: (answers: { question_id: string; value: number }[]) => Promise<import('../api/survey').SurveyResult>;
  // 자가진단 이력이 아예 없으면(한 번도 검사 안 함) 404 대신 null을 돌려준다 — 백엔드의
  // "명시적으로 404"를 프론트 쪽에서 "빈 상태"로 변환하는 지점.
  getLatestSurvey: () => Promise<import('../api/survey').SurveyResult | null>;
  getSurveyHistory: (limit?: number) => Promise<import('../api/survey').SurveyResult[]>;

  // DART 공시/뉴스 — 중요도 필터 없이 최신순 그대로
  getNews: (limit?: number, offset?: number, period?: string) => Promise<DartNews[]>;
  getRelatedNews: (tradeId: number, limit?: number) => Promise<DartNews[]>;
  // 전체 소식 화면의 기간 필터용 — 해당 기간에 해당하는 공시를 끝까지 페이지네이션 순회해서 모아옴.
  getAllNews: (period: string) => Promise<DartNews[]>;

  // 계좌 단위 편향 점수(성향분석 탭 "검사 결과 vs 실제 거래 데이터" 비교용) — 서버가 편향마다
  // 의미 있는 매수/매도 방향만 골라 평균 낸 값. 해당 방향 거래가 없으면 score가 null.
  getAccountBiasScores: () => Promise<import('../api/coach').AccountBiasScoresResponse>;
}

const AppStateContext = createContext<AppStateValue | null>(null);

export function AppStateProvider({ children }: { children: React.ReactNode }) {
  const [journals, setJournals] = useState<JournalApiItem[]>([]);
  const [notif, setNotif] = useState(true);

  const [authPhase, setAuthPhase] = useState<AuthPhase>('auth');
  const [authReady, setAuthReady] = useState(false);
  const [onboardingDone, setOnboardingDone] = useState(false);
  const [keepLogin, setKeepLogin] = useState(true);
  const [pfEmail, setPfEmail] = useState('');
  // 온보딩 완료 기록을 계정별로 저장/삭제하기 위한 현재 로그인 계정 id.
  const [userId, setUserId] = useState<number | null>(null);

  useEffect(() => {
    // 로그인 상태 유지된 사용자는 스플래시 화면(App.tsx)이 최소 이만큼은 보인 뒤에
    // 바로 홈으로 넘어가게 함 — 저장소 조회가 순식간에 끝나서 스플래시가 깜빡이듯
    // 스쳐 지나가는 걸 방지. 로그인 안 된 사용자는 이 지연 없이 바로 AuthNavigator로
    // 넘어가고, 거기 있는 SplashScreen이 자기 타이머로 스플래시를 보여줌.
    const MIN_SPLASH_MS = 1500;
    const startedAt = Date.now();
    (async () => {
      try {
        const [token, keepLoginRaw, pendingUploadRaw] = await Promise.all([
          getToken(),
          AsyncStorage.getItem(KEEP_LOGIN_STORAGE_KEY),
          AsyncStorage.getItem(PENDING_UPLOAD_STORAGE_KEY),
        ]);
        // 온보딩 완료 여부는 계정별 키라 user id를 알아야 읽을 수 있다 — getMe() 이후로 미룬다.
        AsyncStorage.removeItem(LEGACY_ONBOARDING_DONE_STORAGE_KEY).catch(() => {});
        if (pendingUploadRaw) {
          try { setPendingUploadState(JSON.parse(pendingUploadRaw)); } catch { /* 손상된 값은 무시 */ }
        }
        const wantsKeepLogin = keepLoginRaw === '1';
        setKeepLogin(wantsKeepLogin);
        // "로그인 상태 유지"를 껐던 세션이면, 토큰이 저장소에 남아있어도(이전 실행 잔재)
        // 자동 로그인을 시도하지 않고 지운다 — 원래 mock 로직의 "keepLogin이 false면
        // 재실행 시 세션이 없는 것처럼 시작" 의도를 실제 토큰 기준으로 그대로 재현.
        if (token && wantsKeepLogin) {
          try {
            const profile = await authApi.getMe();
            setUserId(profile.id);
            setPfName(profile.name);
            setPfEmail(profile.email ?? '');
            notificationsApi.getNotifications().then((res) => {
              setNotifications(res.notifications);
              setUnreadNotifCount(res.unread_count);
            }).catch(() => {});
            const effectiveOnboardingDone = await resolveOnboardingDone(profile.id);
            setOnboardingDone(effectiveOnboardingDone);
            const elapsed = Date.now() - startedAt;
            if (elapsed < MIN_SPLASH_MS) await new Promise((r) => setTimeout(r, MIN_SPLASH_MS - elapsed));
            setAuthPhase(effectiveOnboardingDone ? 'main' : 'onboarding');
          } catch {
            // 토큰 만료/무효 — 응답 인터셉터가 이미 토큰을 지웠으므로 로그인 화면부터 시작
          }
        } else if (token) {
          await clearToken();
        }
      } catch {
        // 저장된 값이 없거나 손상된 경우 로그인 화면부터 시작
      } finally {
        setAuthReady(true);
      }
    })();
  }, []);

  const [tutStep, setTutStep] = useState(0);
  const [rulesConfirmed, setRulesConfirmed] = useState(false);

  const [ruleOn, setRuleOn] = useState<RuleOnMap>(() =>
    Object.fromEntries(RULES.map((r) => [r.id, r.defaultOn]))
  );
  const [ruleVal, setRuleValState] = useState<RuleValMap>(() =>
    Object.fromEntries(RULES.map((r) => [r.id, r.defaultVal]))
  );
  const [ruleMoney, setRuleMoneyState] = useState<RuleValMap>(() =>
    Object.fromEntries(RULES.filter((r) => r.isMoney).map((r) => [r.id, 0]))
  );
  const ruleSnapRef = useRef<RuleSnapshot | null>(null);
  // 규칙 조언 카드를 거쳐 켠 규칙의 id — saveRules가 이 규칙에만 source:'recommendation'을
  // 보내고, 저장(성공) 또는 취소(ruleRevert) 시 비운다.
  const recommendedRuleIdRef = useRef<string | null>(null);

  const [upFile, setUpFile] = useState<UpFile | null>(null);
  const [pendingUpload, setPendingUploadState] = useState<PendingUpload | null>(null);

  const [notifications, setNotifications] = useState<NotificationApiItem[]>([]);
  const [unreadNotifCount, setUnreadNotifCount] = useState(0);
  const [osNotif, setOsNotif] = useState<'granted' | 'denied' | 'unset'>('unset');
  const [notifPermModalOpen, setNotifPermModalOpen] = useState(false);
  const [biasInfo, setBiasInfo] = useState(false);
  const [pfName, setPfName] = useState('김투자');

  const refreshJournals = useCallback(async () => {
    const PAGE = 100;
    const MAX_PAGES = 10; // 안전장치 — 최대 1000건까지만 순회
    let offset = 0;
    const all: JournalApiItem[] = [];
    for (let i = 0; i < MAX_PAGES; i++) {
      const page = await journalsApi.getJournals(PAGE, offset);
      all.push(...page);
      if (page.length < PAGE) break;
      offset += PAGE;
    }
    setJournals(all);
  }, []);

  const saveJournal = useCallback<AppStateValue['saveJournal']>(async (journalId, patch) => {
    const updated = await journalsApi.updateJournal(journalId, patch.emotion, patch.reason, patch.review);
    setJournals((prev) => prev.map((j) => (j.id === journalId ? updated : j)));
  }, []);

  const createJournalEntry = useCallback<AppStateValue['createJournalEntry']>(async (tradeId, patch) => {
    const created = await journalsApi.createJournal(tradeId, patch.emotion, patch.reason, patch.review);
    setJournals((prev) => [created, ...prev]);
  }, []);

  const deleteJournal = useCallback(async (journalId: number) => {
    await journalsApi.deleteJournal(journalId);
    setJournals((prev) => prev.filter((j) => j.id !== journalId));
  }, []);

  const isJournaled = useCallback(
    (tradeId: number) => journals.some((j) => j.trade_id === tradeId),
    [journals]
  );

  const login = useCallback(async (email: string, password: string) => {
    const { access_token } = await authApi.login(email, password);
    await setToken(access_token);
    // 토큰 자체는(이번 세션 API 호출을 위해) keepLogin과 무관하게 항상 저장하고,
    // "다음 실행 때 이걸 신뢰해도 되는지"만 이 플래그로 따로 남긴다 — 부팅 시
    // keepLogin이 꺼져있었으면 남아있는 토큰을 무시하고 지운다.
    await AsyncStorage.setItem(KEEP_LOGIN_STORAGE_KEY, keepLogin ? '1' : '0');
    const profile = await authApi.getMe();
    setUserId(profile.id);
    setPfName(profile.name);
    setPfEmail(profile.email ?? '');
    notificationsApi.getNotifications().then((res) => {
      setNotifications(res.notifications);
      setUnreadNotifCount(res.unread_count);
    }).catch(() => {});
    // 직전에 다른 계정으로 쓰던 메모리 상태가 아니라, 이 계정의 기록으로만 판단한다.
    const effectiveOnboardingDone = await resolveOnboardingDone(profile.id);
    setOnboardingDone(effectiveOnboardingDone);
    setAuthPhase(effectiveOnboardingDone ? 'main' : 'onboarding');
  }, [keepLogin]);

  const enterMainDirectly = useCallback(() => {
    setOnboardingDone(true);
    setAuthPhase('main');
    if (userId != null) AsyncStorage.setItem(onboardingDoneKey(userId), '1').catch(() => {});
  }, [userId]);

  const clearPendingUpload = useCallback(() => {
    setPendingUploadState(null);
    AsyncStorage.removeItem(PENDING_UPLOAD_STORAGE_KEY).catch(() => {});
  }, []);

  const uploadFile = useCallback(async (fileUri: string, fileName: string, mimeType: string, webFile?: File) => {
    const res = await tradesApi.uploadTrades(fileUri, fileName, mimeType, webFile);
    const pending: PendingUpload = { uploadId: res.upload_id, jobId: res.job_id, fileName };
    setPendingUploadState(pending);
    AsyncStorage.setItem(PENDING_UPLOAD_STORAGE_KEY, JSON.stringify(pending)).catch(() => {});
    // 업로드 접수 시점에 서버가 바로 'upload' 알림을 쌓으므로 벨 배지를 즉시 갱신.
    notificationsApi.getNotifications().then((r) => {
      setNotifications(r.notifications);
      setUnreadNotifCount(r.unread_count);
    }).catch(() => {});
    return res;
  }, []);

  const pollJobStatus = useCallback(async (jobId: number) => {
    const status = await tradesApi.getJobStatus(jobId);
    // 분석이 끝나는 순간(성공/실패) 서버가 알림을 쌓으므로 그때 한 번 더 갱신.
    if (status.status === 'done' || status.status === 'failed') {
      notificationsApi.getNotifications().then((r) => {
        setNotifications(r.notifications);
        setUnreadNotifCount(r.unread_count);
      }).catch(() => {});
    }
    return status;
  }, []);

  const getUploads = useCallback(async (limit?: number, offset?: number) => {
    return tradesApi.getUploads(limit, offset);
  }, []);

  const getAllAnalysis = useCallback(async () => {
    const PAGE = 200;
    const MAX_PAGES = 10; // 안전장치 — 최대 2000건까지만 순회
    let offset = 0;
    const all: import('../api/analysis').AnalysisResult[] = [];
    for (let i = 0; i < MAX_PAGES; i++) {
      const page = await analysisApi.getAnalysis(PAGE, offset);
      all.push(...page);
      if (page.length < PAGE) break;
      offset += PAGE;
    }
    return all;
  }, []);

  const getAllTrades = useCallback(async () => {
    const PAGE = 200;
    const MAX_PAGES = 10;
    let offset = 0;
    const all: import('../api/trades').TradeRaw[] = [];
    for (let i = 0; i < MAX_PAGES; i++) {
      const page = await tradesApi.getTrades(PAGE, offset);
      all.push(...page);
      if (page.length < PAGE) break;
      offset += PAGE;
    }
    return all;
  }, []);

  const getNews = useCallback(async (limit?: number, offset?: number, period?: string) => {
    return newsApi.getNews(limit, offset, period);
  }, []);

  const getRelatedNews = useCallback(async (tradeId: number, limit?: number) => {
    return newsApi.getRelatedNews(tradeId, limit);
  }, []);

  const getAllNews = useCallback(async (period: string) => {
    const PAGE = 100;
    const MAX_PAGES = 10; // 안전장치 — 최대 1000건까지만 순회
    let offset = 0;
    const all: DartNews[] = [];
    for (let i = 0; i < MAX_PAGES; i++) {
      const page = await newsApi.getNews(PAGE, offset, period);
      all.push(...page);
      if (page.length < PAGE) break;
      offset += PAGE;
    }
    return all;
  }, []);

  const getAccountBiasScores = useCallback(async () => {
    return coachApi.getAccountBiasScores();
  }, []);

  const logout = useCallback(async () => {
    setAuthPhase('auth');
    await clearToken();
    await AsyncStorage.removeItem(KEEP_LOGIN_STORAGE_KEY);
    // 다른 계정이 같은 기기에서 로그인했을 때 남의 진행 중 업로드를 이어받지 않도록.
    clearPendingUpload();
    setNotifications([]);
    setUnreadNotifCount(0);
    // 다음에 로그인하는 계정이 이 계정의 온보딩 여부를 물려받지 않도록 메모리 상태만 되돌린다
    // (저장된 계정별 기록은 그 계정이 다시 로그인할 때 쓰도록 그대로 둔다).
    setUserId(null);
    setOnboardingDone(false);
  }, [clearPendingUpload]);

  // 회원가입 자체는 토큰을 발급받지만(자동 로그인 가능) 제품 결정상 쓰지 않고 버린다 —
  // 가입 후엔 항상 로그인 화면으로 보내서 사용자가 명시적으로 다시 로그인하게 함.
  const signup = useCallback<AppStateValue['signup']>(async (params) => {
    await authApi.signup(params);
  }, []);

  const verifyEmail = useCallback(async (email: string, code: string) => {
    await authApi.verifyEmail(email, code);
  }, []);

  const resendVerification = useCallback(async (email: string) => {
    await authApi.resendVerification(email);
  }, []);

  const requestPasswordReset = useCallback(async (email: string) => {
    await authApi.passwordResetRequest(email);
  }, []);

  const confirmPasswordReset = useCallback(async (email: string, code: string, newPassword: string) => {
    await authApi.passwordResetConfirm(email, code, newPassword);
  }, []);

  const submitSurvey = useCallback(async (answers: { question_id: string; value: number }[]) => {
    return surveyApi.submitSurvey(answers);
  }, []);

  const getLatestSurvey = useCallback(async () => {
    try {
      return await surveyApi.getLatestSurvey();
    } catch (e: any) {
      if (e?.response?.status === 404) return null;
      throw e;
    }
  }, []);

  const getSurveyHistory = useCallback(async (limit?: number) => {
    return surveyApi.getSurveyHistory(limit);
  }, []);

  const updateProfileName = useCallback(async (name: string) => {
    const profile = await authApi.updateProfile(name);
    setPfName(profile.name);
  }, []);

  const changePassword = useCallback(async (currentPassword: string, newPassword: string) => {
    await authApi.changePassword(currentPassword, newPassword);
  }, []);

  const withdrawAccount = useCallback(async () => {
    await authApi.withdraw();
    setAuthPhase('auth');
    await clearToken();
    await AsyncStorage.removeItem(KEEP_LOGIN_STORAGE_KEY);
    // 탈퇴한 계정의 온보딩 기록은 되살아날 일이 없으니 아예 지운다.
    if (userId != null) await AsyncStorage.removeItem(onboardingDoneKey(userId)).catch(() => {});
    setUserId(null);
    setOnboardingDone(false);
    clearPendingUpload();
    setNotifications([]);
    setUnreadNotifCount(0);
  }, [clearPendingUpload, userId]);

  // 401(토큰 만료/무효) 응답을 받으면 어느 화면에 있든 로그인 화면으로 돌려보낸다.
  useEffect(() => {
    setUnauthorizedHandler(() => { logout(); });
  }, [logout]);

  const completeOnboarding = useCallback(() => {
    setOnboardingDone(true);
    setAuthPhase('main');
    setNotifPermModalOpen(true);
    if (userId != null) AsyncStorage.setItem(onboardingDoneKey(userId), '1').catch(() => {});
  }, [userId]);

  const toggleRule = useCallback((id: string) => {
    setRuleOn((prev) => ({ ...prev, [id]: !prev[id] }));
  }, []);

  const setRuleVal = useCallback((id: string, val: number) => {
    setRuleValState((prev) => ({ ...prev, [id]: val }));
  }, []);

  const setRuleMoney = useCallback((id: string, val: number) => {
    setRuleMoneyState((prev) => ({ ...prev, [id]: val }));
  }, []);

  const ruleSnap = useCallback(() => {
    ruleSnapRef.current = { ruleOn, ruleVal, ruleMoney };
  }, [ruleOn, ruleVal, ruleMoney]);

  const ruleRevert = useCallback(() => {
    const snap = ruleSnapRef.current;
    if (snap) {
      setRuleOn(snap.ruleOn);
      setRuleValState(snap.ruleVal);
      setRuleMoneyState(snap.ruleMoney);
      ruleSnapRef.current = null;
    }
    recommendedRuleIdRef.current = null;
  }, []);

  const prefillRuleFromAdvice = useCallback((ruleId: string, param: number) => {
    recommendedRuleIdRef.current = ruleId;
    setRuleOn((prev) => ({ ...prev, [ruleId]: true }));
    const template = RULES.find((r) => r.id === ruleId);
    if (template?.isMoney) setRuleMoneyState((prev) => ({ ...prev, [ruleId]: param }));
    else setRuleValState((prev) => ({ ...prev, [ruleId]: param }));
  }, []);

  // 서버의 규칙 7종 상태를 불러와 ruleOn/ruleVal/ruleMoney에 채운다. 백엔드는
  // 규칙당 param 필드 하나뿐이라, RULES(mock.ts) 템플릿의 isMoney/unit 여부를 보고
  // ruleVal(횟수·일수)과 ruleMoney(금액) 중 어디에 넣을지 프론트에서 나눠 담는다.
  const loadRules = useCallback(async () => {
    const items = await rulesApi.getRules();
    const nextOn: RuleOnMap = {};
    const nextVal: RuleValMap = {};
    const nextMoney: RuleValMap = {};
    items.forEach((item) => {
      nextOn[item.rule_id] = item.enabled;
      const template = RULES.find((r) => r.id === item.rule_id);
      const param = item.param ?? template?.defaultVal ?? 0;
      if (template?.isMoney) nextMoney[item.rule_id] = param;
      else if (template && template.unit !== null) nextVal[item.rule_id] = param;
    });
    setRuleOn(nextOn);
    setRuleValState(nextVal);
    setRuleMoneyState(nextMoney);
    ruleSnapRef.current = { ruleOn: nextOn, ruleVal: nextVal, ruleMoney: nextMoney };
  }, []);

  // 7종 규칙 전부를 현재 로컬 상태 그대로 PUT — 두 맵(ruleVal/ruleMoney)을 다시
  // param 필드 하나로 합친다. same_day_roundtrip처럼 파라미터가 없는 규칙은 null.
  // 규칙 조언 카드를 거쳐온 규칙(recommendedRuleIdRef)만 source:'recommendation'으로 보낸다.
  const saveRules = useCallback(async () => {
    const recommendedId = recommendedRuleIdRef.current;
    await Promise.all(RULES.map((template) => {
      const enabled = !!ruleOn[template.id];
      const param = template.isMoney
        ? (ruleMoney[template.id] || null)
        : template.unit !== null
          ? (ruleVal[template.id] ?? null)
          : null;
      const source = template.id === recommendedId ? 'recommendation' : undefined;
      return rulesApi.setRule(template.id, enabled, param, source);
    }));
    recommendedRuleIdRef.current = null;
    ruleSnapRef.current = { ruleOn, ruleVal, ruleMoney };
  }, [ruleOn, ruleVal, ruleMoney]);

  const getRuleEffect = useCallback(async (ruleId: string, param?: number | null) => {
    return rulesApi.getRuleEffect(ruleId, param);
  }, []);

  const refreshNotifications = useCallback(async () => {
    const res = await notificationsApi.getNotifications();
    setNotifications(res.notifications);
    setUnreadNotifCount(res.unread_count);
  }, []);

  const markNotifRead = useCallback((id: number) => {
    setNotifications((prev) => {
      const target = prev.find((n) => n.id === id);
      if (target && !target.is_read) setUnreadNotifCount((c) => Math.max(0, c - 1));
      return prev.map((n) => (n.id === id ? { ...n, is_read: true } : n));
    });
    notificationsApi.markNotificationRead(id).catch(() => {});
  }, []);

  const markAllNotifRead = useCallback(() => {
    setNotifications((prev) => {
      const unread = prev.filter((n) => !n.is_read);
      unread.forEach((n) => { notificationsApi.markNotificationRead(n.id).catch(() => {}); });
      return prev.map((n) => ({ ...n, is_read: true }));
    });
    setUnreadNotifCount(0);
  }, []);

  const requestNotifPermission = useCallback((allow: boolean) => {
    setOsNotif(allow ? 'granted' : 'denied');
    setNotif(allow);
    setNotifPermModalOpen(false);
  }, []);

  const closeNotifPermModal = useCallback(() => setNotifPermModalOpen(false), []);

  const openBiasInfo = useCallback(() => setBiasInfo(true), []);
  const closeBiasInfo = useCallback(() => setBiasInfo(false), []);

  const value = useMemo<AppStateValue>(
    () => ({
      journals,
      refreshJournals,
      saveJournal,
      createJournalEntry,
      deleteJournal,
      isJournaled,
      notif,
      toggleNotif: () => setNotif((v) => !v),
      authPhase,
      authReady,
      login,
      enterMainDirectly,
      logout,
      completeOnboarding,
      onboardingDone,
      keepLogin,
      setKeepLogin,
      tutStep,
      setTutStep,
      rulesConfirmed,
      setRulesConfirmed,
      ruleOn,
      ruleVal,
      ruleMoney,
      toggleRule,
      setRuleVal,
      setRuleMoney,
      ruleSnap,
      ruleRevert,
      loadRules,
      saveRules,
      upFile,
      setUpFile,
      uploadFile,
      pollJobStatus,
      getUploads,
      getAllAnalysis,
      getAllTrades,
      pendingUpload,
      clearPendingUpload,
      notifications,
      refreshNotifications,
      markNotifRead,
      markAllNotifRead,
      unreadNotifCount,
      osNotif,
      requestNotifPermission,
      notifPermModalOpen,
      closeNotifPermModal,
      biasInfo,
      openBiasInfo,
      closeBiasInfo,
      pfName,
      setPfName,
      pfEmail,
      updateProfileName,
      changePassword,
      withdrawAccount,
      signup,
      verifyEmail,
      resendVerification,
      requestPasswordReset,
      confirmPasswordReset,
      submitSurvey,
      getLatestSurvey,
      getSurveyHistory,
      getNews,
      getRelatedNews,
      getAllNews,
      getAccountBiasScores,
      prefillRuleFromAdvice,
      getRuleEffect,
    }),
    [
      journals, refreshJournals, saveJournal, createJournalEntry, deleteJournal, isJournaled, notif,
      authPhase, authReady, login, enterMainDirectly, logout, completeOnboarding, onboardingDone, keepLogin,
      tutStep, rulesConfirmed,
      ruleOn, ruleVal, ruleMoney, toggleRule, setRuleVal, setRuleMoney, ruleSnap, ruleRevert, loadRules, saveRules,
      prefillRuleFromAdvice, getRuleEffect,
      upFile, uploadFile, pollJobStatus, getUploads, getAllAnalysis, getAllTrades, pendingUpload, clearPendingUpload,
      notifications, refreshNotifications, markNotifRead, markAllNotifRead, unreadNotifCount,
      osNotif, requestNotifPermission, notifPermModalOpen, closeNotifPermModal,
      biasInfo, openBiasInfo, closeBiasInfo, pfName, pfEmail,
      updateProfileName, changePassword, withdrawAccount,
      signup, verifyEmail, resendVerification, requestPasswordReset, confirmPasswordReset, submitSurvey,
      getLatestSurvey, getSurveyHistory,
      getNews, getRelatedNews, getAllNews, getAccountBiasScores,
    ]
  );

  return <AppStateContext.Provider value={value}>{children}</AppStateContext.Provider>;
}

export function useAppState() {
  const ctx = useContext(AppStateContext);
  if (!ctx) throw new Error('useAppState must be used within AppStateProvider');
  return ctx;
}
