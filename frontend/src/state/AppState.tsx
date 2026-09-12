import React, { createContext, useContext, useState, useCallback, useMemo, useRef, useEffect } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { journals as journalsSeed, RULES, NOTIFS } from '../data/mock';
import type { Journal } from '../data/types';
import { getToken, setToken, clearToken, setUnauthorizedHandler } from '../api/client';
import * as authApi from '../api/auth';
import * as surveyApi from '../api/survey';

export type AuthPhase = 'auth' | 'onboarding' | 'main';

// "로그인 상태 유지" 체크 여부 — 꺼져있으면 앱을 재실행했을 때 토큰이 저장소에
// 남아있어도 자동 로그인을 시도하지 않는다(로그인 시점에 같이 기록).
const KEEP_LOGIN_STORAGE_KEY = '@canary/keepLogin';

// 튜토리얼(온보딩)을 한 번이라도 완료했는지 — "로그인 상태 유지"와 별개로 항상 저장됨.
// 로그아웃하거나 로그인 상태 유지를 꺼도 이 기록은 남아있어서, 다시 로그인하면 튜토리얼을 또 보여주지 않음.
const ONBOARDING_DONE_STORAGE_KEY = '@canary/onboardingDone';

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
}

interface AppStateValue {
  // 거래일지
  journals: Journal[];
  saveJournal: (journalId: number | null, patch: { reason: string; emotion: string; review: string }) => void;
  addJournal: (journal: Journal) => void;
  deleteJournal: (journalId: number) => void;
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

  // 업로드 플로우
  upFile: UpFile | null;
  setUpFile: (f: UpFile | null) => void;

  // 알림 목록
  notifRead: Record<number, boolean>;
  markNotifRead: (idx: number) => void;
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

  // 거래 내역 업로드 여부(빈 상태 화면 분기용) — 개발용 토글, 추후 API 연동 시 실제 업로드 데이터 유무로 대체
  hasUploaded: boolean;
  toggleHasUploaded: () => void;
}

const AppStateContext = createContext<AppStateValue | null>(null);

export function AppStateProvider({ children }: { children: React.ReactNode }) {
  const [journals, setJournals] = useState<Journal[]>(journalsSeed);
  const [notif, setNotif] = useState(true);

  const [authPhase, setAuthPhase] = useState<AuthPhase>('auth');
  const [authReady, setAuthReady] = useState(false);
  const [onboardingDone, setOnboardingDone] = useState(false);
  const [keepLogin, setKeepLogin] = useState(true);
  const [pfEmail, setPfEmail] = useState('');

  useEffect(() => {
    // 로그인 상태 유지된 사용자는 스플래시 화면(App.tsx)이 최소 이만큼은 보인 뒤에
    // 바로 홈으로 넘어가게 함 — 저장소 조회가 순식간에 끝나서 스플래시가 깜빡이듯
    // 스쳐 지나가는 걸 방지. 로그인 안 된 사용자는 이 지연 없이 바로 AuthNavigator로
    // 넘어가고, 거기 있는 SplashScreen이 자기 타이머로 스플래시를 보여줌.
    const MIN_SPLASH_MS = 1500;
    const startedAt = Date.now();
    (async () => {
      try {
        const [token, keepLoginRaw, onboardingRaw] = await Promise.all([
          getToken(),
          AsyncStorage.getItem(KEEP_LOGIN_STORAGE_KEY),
          AsyncStorage.getItem(ONBOARDING_DONE_STORAGE_KEY),
        ]);
        const savedOnboardingDone = onboardingRaw === '1';
        if (savedOnboardingDone) setOnboardingDone(true);
        const wantsKeepLogin = keepLoginRaw === '1';
        setKeepLogin(wantsKeepLogin);
        // "로그인 상태 유지"를 껐던 세션이면, 토큰이 저장소에 남아있어도(이전 실행 잔재)
        // 자동 로그인을 시도하지 않고 지운다 — 원래 mock 로직의 "keepLogin이 false면
        // 재실행 시 세션이 없는 것처럼 시작" 의도를 실제 토큰 기준으로 그대로 재현.
        if (token && wantsKeepLogin) {
          try {
            const profile = await authApi.getMe();
            setPfName(profile.name);
            setPfEmail(profile.email ?? '');
            const elapsed = Date.now() - startedAt;
            if (elapsed < MIN_SPLASH_MS) await new Promise((r) => setTimeout(r, MIN_SPLASH_MS - elapsed));
            setAuthPhase(savedOnboardingDone ? 'main' : 'onboarding');
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

  const [upFile, setUpFile] = useState<UpFile | null>(null);

  const [notifRead, setNotifRead] = useState<Record<number, boolean>>({});
  const [osNotif, setOsNotif] = useState<'granted' | 'denied' | 'unset'>('unset');
  const [notifPermModalOpen, setNotifPermModalOpen] = useState(false);
  const [biasInfo, setBiasInfo] = useState(false);
  const [pfName, setPfName] = useState('김투자');
  const [hasUploaded, setHasUploaded] = useState(true);

  const saveJournal = useCallback<AppStateValue['saveJournal']>((journalId, patch) => {
    setJournals((prev) => {
      if (journalId == null) return prev;
      return prev.map((j) => (j.id === journalId ? { ...j, ...patch } : j));
    });
  }, []);

  const addJournal = useCallback((journal: Journal) => {
    setJournals((prev) => (prev.some((j) => j.id === journal.id) ? prev : [journal, ...prev]));
  }, []);

  const deleteJournal = useCallback((journalId: number) => {
    setJournals((prev) => prev.filter((j) => j.id !== journalId));
  }, []);

  const isJournaled = useCallback(
    (tradeId: number) => journals.some((j) => j.id === tradeId),
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
    setPfName(profile.name);
    setPfEmail(profile.email ?? '');
    setAuthPhase(onboardingDone ? 'main' : 'onboarding');
  }, [onboardingDone, keepLogin]);

  const enterMainDirectly = useCallback(() => {
    setOnboardingDone(true);
    setAuthPhase('main');
    AsyncStorage.setItem(ONBOARDING_DONE_STORAGE_KEY, '1').catch(() => {});
  }, []);

  const logout = useCallback(async () => {
    setAuthPhase('auth');
    await clearToken();
    await AsyncStorage.removeItem(KEEP_LOGIN_STORAGE_KEY);
  }, []);

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
  }, []);

  // 401(토큰 만료/무효) 응답을 받으면 어느 화면에 있든 로그인 화면으로 돌려보낸다.
  useEffect(() => {
    setUnauthorizedHandler(() => { logout(); });
  }, [logout]);

  const completeOnboarding = useCallback(() => {
    setOnboardingDone(true);
    setAuthPhase('main');
    setNotifPermModalOpen(true);
    AsyncStorage.setItem(ONBOARDING_DONE_STORAGE_KEY, '1').catch(() => {});
  }, []);

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
  }, []);

  const markNotifRead = useCallback((idx: number) => {
    setNotifRead((prev) => ({ ...prev, [idx]: true }));
  }, []);

  const markAllNotifRead = useCallback(() => {
    setNotifRead(Object.fromEntries(NOTIFS.map((_, i) => [i, true])));
  }, []);

  const unreadNotifCount = useMemo(
    () => NOTIFS.reduce((n, _, i) => (notifRead[i] ? n : n + 1), 0),
    [notifRead]
  );

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
      saveJournal,
      addJournal,
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
      upFile,
      setUpFile,
      notifRead,
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
      hasUploaded,
      toggleHasUploaded: () => setHasUploaded((v) => !v),
    }),
    [
      journals, saveJournal, addJournal, deleteJournal, isJournaled, notif,
      authPhase, authReady, login, enterMainDirectly, logout, completeOnboarding, onboardingDone, keepLogin,
      tutStep, rulesConfirmed,
      ruleOn, ruleVal, ruleMoney, toggleRule, setRuleVal, setRuleMoney, ruleSnap, ruleRevert,
      upFile,
      notifRead, markNotifRead, markAllNotifRead, unreadNotifCount,
      osNotif, requestNotifPermission, notifPermModalOpen, closeNotifPermModal,
      biasInfo, openBiasInfo, closeBiasInfo, pfName, pfEmail,
      updateProfileName, changePassword, withdrawAccount,
      signup, verifyEmail, resendVerification, requestPasswordReset, confirmPasswordReset, submitSurvey,
      hasUploaded,
    ]
  );

  return <AppStateContext.Provider value={value}>{children}</AppStateContext.Provider>;
}

export function useAppState() {
  const ctx = useContext(AppStateContext);
  if (!ctx) throw new Error('useAppState must be used within AppStateProvider');
  return ctx;
}
