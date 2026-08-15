import React, { createContext, useContext, useState, useCallback, useMemo } from 'react';
import { journals as journalsSeed } from '../data/mock';
import type { Journal } from '../data/types';

interface AppStateValue {
  journals: Journal[];
  saveJournal: (journalId: number | null, patch: { reason: string; emotion: string; review: string }) => void;
  notif: boolean;
  auto: boolean;
  toggleNotif: () => void;
  toggleAuto: () => void;
}

const AppStateContext = createContext<AppStateValue | null>(null);

export function AppStateProvider({ children }: { children: React.ReactNode }) {
  const [journals, setJournals] = useState<Journal[]>(journalsSeed);
  const [notif, setNotif] = useState(true);
  const [auto, setAuto] = useState(true);

  const saveJournal = useCallback<AppStateValue['saveJournal']>((journalId, patch) => {
    setJournals((prev) => {
      if (journalId == null) return prev;
      return prev.map((j) => (j.id === journalId ? { ...j, ...patch } : j));
    });
  }, []);

  const value = useMemo<AppStateValue>(
    () => ({
      journals,
      saveJournal,
      notif,
      auto,
      toggleNotif: () => setNotif((v) => !v),
      toggleAuto: () => setAuto((v) => !v),
    }),
    [journals, saveJournal, notif, auto]
  );

  return <AppStateContext.Provider value={value}>{children}</AppStateContext.Provider>;
}

export function useAppState() {
  const ctx = useContext(AppStateContext);
  if (!ctx) throw new Error('useAppState must be used within AppStateProvider');
  return ctx;
}
