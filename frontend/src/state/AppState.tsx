import React, { createContext, useContext, useState, useCallback, useMemo, useRef } from 'react';
import { journals as journalsSeed, RULES, NOTIFS } from '../data/mock';
import type { Journal } from '../data/types';

export type AuthPhase = 'auth' | 'onboarding' | 'main';

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
  isJournaled: (tradeId: number) => boolean;

  // 설정 — 알림
  notif: boolean;
  toggleNotif: () => void;

  // 인증 / 온보딩 플로우
  authPhase: AuthPhase;
  login: () => void;
  enterMainDirectly: () => void;
  logout: () => void;
  completeOnboarding: () => void;
  onboardingDone: boolean;
  keepLogin: boolean;
  setKeepLogin: (v: boolean) => void;
  suVerified: boolean;
  setSuVerified: (v: boolean) => void;

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
}

const AppStateContext = createContext<AppStateValue | null>(null);

export function AppStateProvider({ children }: { children: React.ReactNode }) {
  const [journals, setJournals] = useState<Journal[]>(journalsSeed);
  const [notif, setNotif] = useState(true);

  const [authPhase, setAuthPhase] = useState<AuthPhase>('auth');
  const [onboardingDone, setOnboardingDone] = useState(false);
  const [keepLogin, setKeepLogin] = useState(true);
  const [suVerified, setSuVerified] = useState(false);

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

  const saveJournal = useCallback<AppStateValue['saveJournal']>((journalId, patch) => {
    setJournals((prev) => {
      if (journalId == null) return prev;
      return prev.map((j) => (j.id === journalId ? { ...j, ...patch } : j));
    });
  }, []);

  const addJournal = useCallback((journal: Journal) => {
    setJournals((prev) => (prev.some((j) => j.id === journal.id) ? prev : [journal, ...prev]));
  }, []);

  const isJournaled = useCallback(
    (tradeId: number) => journals.some((j) => j.id === tradeId),
    [journals]
  );

  const login = useCallback(() => {
    setAuthPhase(onboardingDone ? 'main' : 'onboarding');
  }, [onboardingDone]);

  const enterMainDirectly = useCallback(() => {
    setAuthPhase('main');
  }, []);

  const logout = useCallback(() => {
    setAuthPhase('auth');
  }, []);

  const completeOnboarding = useCallback(() => {
    setOnboardingDone(true);
    setAuthPhase('main');
    setNotifPermModalOpen(true);
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
      isJournaled,
      notif,
      toggleNotif: () => setNotif((v) => !v),
      authPhase,
      login,
      enterMainDirectly,
      logout,
      completeOnboarding,
      onboardingDone,
      keepLogin,
      setKeepLogin,
      suVerified,
      setSuVerified,
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
    }),
    [
      journals, saveJournal, addJournal, isJournaled, notif,
      authPhase, login, enterMainDirectly, logout, completeOnboarding, onboardingDone, keepLogin,
      suVerified, tutStep, rulesConfirmed,
      ruleOn, ruleVal, ruleMoney, toggleRule, setRuleVal, setRuleMoney, ruleSnap, ruleRevert,
      upFile,
      notifRead, markNotifRead, markAllNotifRead, unreadNotifCount,
      osNotif, requestNotifPermission, notifPermModalOpen, closeNotifPermModal,
      biasInfo, openBiasInfo, closeBiasInfo, pfName,
    ]
  );

  return <AppStateContext.Provider value={value}>{children}</AppStateContext.Provider>;
}

export function useAppState() {
  const ctx = useContext(AppStateContext);
  if (!ctx) throw new Error('useAppState must be used within AppStateProvider');
  return ctx;
}
