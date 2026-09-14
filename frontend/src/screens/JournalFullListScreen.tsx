import React, { useCallback, useMemo, useState } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { Screen } from '../components/Screen';
import { Card } from '../components/Card';
import { EmptyState } from '../components/EmptyState';
import { JournalRow } from '../components/JournalRow';
import { PeriodDropdown } from '../components/PeriodDropdown';
import { TypeTabs, SortToggle, SearchInput, RiskChips, Pagination, TypeFilter, RiskFilter } from '../components/FilterControls';
import { C, PERIODS, text } from '../theme/tokens';
import type { TradeRaw } from '../api/trades';
import type { AnalysisResult } from '../api/analysis';
import { formatDate } from '../utils/formatDate';
import { isWithinPeriod } from '../utils/periodFilter';
import { buildAnalysisLookup, findAnalysisForTrade, verdictToRisk } from '../utils/matchTradeAnalysis';
import { useAppState } from '../state/AppState';
import { goToJournalWrite } from '../navigation/navigationRef';

const PAGE_SIZE = 10;

export function JournalFullListScreen() {
  const { journals, refreshJournals, getAllTrades, getAllAnalysis } = useAppState();
  const [trades, setTrades] = useState<TradeRaw[]>([]);
  const [analysis, setAnalysis] = useState<AnalysisResult[]>([]);
  const [type, setType] = useState<TypeFilter>('all');
  const [risk, setRisk] = useState<RiskFilter>('all');
  const [search, setSearch] = useState('');
  const [newest, setNewest] = useState(true);
  const [period, setPeriod] = useState(PERIODS[3]);
  const [page, setPage] = useState(0);
  const isDefaultFilter = type === 'all' && risk === 'all' && search === '';

  useFocusEffect(
    useCallback(() => {
      let cancelled = false;
      (async () => {
        try {
          const [tradesRes, analysisRes] = await Promise.all([getAllTrades(), getAllAnalysis()]);
          if (!cancelled) {
            setTrades(tradesRes);
            setAnalysis(analysisRes);
          }
        } catch {
          // 네트워크 실패 — 이전 값 유지
        }
      })();
      // 일지 목록은 별도 상태(AppState)라 실패해도 위 거래/분석 표시를 막으면 안 되므로 독립적으로 불러온다.
      refreshJournals().catch(() => {});
      return () => { cancelled = true; };
    }, [getAllTrades, getAllAnalysis, refreshJournals])
  );

  const hasUploaded = trades.length > 0;
  const analysisLookup = useMemo(() => buildAnalysisLookup(analysis), [analysis]);
  const tradeById = useMemo(() => new Map(trades.map((t) => [t.id, t])), [trades]);

  const withRisk = useMemo(
    () => journals.map((j) => {
      const t = tradeById.get(j.trade_id);
      const match = t ? findAnalysisForTrade(analysisLookup, t) : null;
      return { journal: j, risk: match ? verdictToRisk(match.detail.verdict) : null };
    }),
    [journals, tradeById, analysisLookup]
  );

  const filtered = useMemo(() => {
    let list = withRisk.filter(({ journal: j, risk: r }) => {
      const jType = j.type === '매도' ? 'sell' : 'buy';
      if (type !== 'all' && jType !== type) return false;
      if (risk !== 'all' && r !== risk) return false;
      if (search && !j.stock.includes(search) && !j.emotion.includes(search)) return false;
      if (!isWithinPeriod(j.date, period)) return false;
      return true;
    });
    if (!newest) list = [...list].reverse();
    return list;
  }, [withRisk, type, risk, search, newest, period]);

  const totalPages = hasUploaded ? Math.max(1, Math.ceil(filtered.length / PAGE_SIZE)) : 1;
  const clampedPage = Math.min(page, totalPages - 1);
  const paginated = filtered.slice(clampedPage * PAGE_SIZE, (clampedPage + 1) * PAGE_SIZE);

  const updateFilter = <T,>(setter: (v: T) => void) => (v: T) => {
    setter(v);
    setPage(0);
  };

  return (
    <Screen back footer={<Pagination page={clampedPage} totalPages={totalPages} onChange={setPage} />}>
      <Text style={text.screenTitle}>전체 거래일지</Text>
      <Text style={[text.screenSubtitle, styles.subtitle]}>기록된 모든 거래를 확인해요</Text>

      <View style={styles.filterRow}>
        <TypeTabs value={type} onChange={updateFilter(setType)} />
        <View style={styles.filterRight}>
          <SortToggle newest={newest} onToggle={() => { setNewest((v) => !v); setPage(0); }} />
          <PeriodDropdown value={period} onChange={(v) => { setPeriod(v); setPage(0); }} />
        </View>
      </View>

      <SearchInput value={search} onChangeText={updateFilter(setSearch)} placeholder="종목명 또는 태그 검색..." />
      <RiskChips value={risk} onChange={updateFilter(setRisk)} />

      {!hasUploaded ? (
        <EmptyState
          title="아직 업로드한 거래 내역이 없어요"
          subtitle={'거래 내역을 업로드하면\n거래마다 일지를 기록할 수 있어요'}
        />
      ) : paginated.length > 0 ? (
        <Card>
          {paginated.map(({ journal: j, risk: r }, i) => (
            <JournalRow
              key={j.id}
              journal={{ ...j, date: formatDate(j.date) }}
              risk={r}
              index={i}
              onPress={() => goToJournalWrite(j.id)}
            />
          ))}
        </Card>
      ) : (
        <Text style={styles.empty}>
          {isDefaultFilter ? `${period}에 해당하는 내역이 없어요` : '검색 결과가 없습니다.'}
        </Text>
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  subtitle: { marginTop: 3, marginBottom: 16 },
  filterRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 13 },
  filterRight: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  empty: { textAlign: 'center', paddingVertical: 40, color: C.muted, fontSize: 16 },
});
