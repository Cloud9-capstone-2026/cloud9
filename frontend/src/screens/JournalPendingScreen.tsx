import React, { useCallback, useMemo, useState } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { Screen } from '../components/Screen';
import { Card } from '../components/Card';
import { TradeRow } from '../components/TradeRow';
import { PeriodDropdown } from '../components/PeriodDropdown';
import { TypeTabs, SortToggle, SearchInput, RiskChips, Pagination, TypeFilter, RiskFilter } from '../components/FilterControls';
import { C, PERIODS, text } from '../theme/tokens';
import type { Trade } from '../data/types';
import type { TradeRaw } from '../api/trades';
import type { AnalysisResult } from '../api/analysis';
import { formatDate } from '../utils/formatDate';
import { isWithinPeriod } from '../utils/periodFilter';
import { buildAnalysisLookup, findAnalysisForTrade, verdictToRisk } from '../utils/matchTradeAnalysis';
import { useAppState } from '../state/AppState';
import { goToJournalWrite } from '../navigation/navigationRef';

const PAGE_SIZE = 10;

function toTradeShape(t: TradeRaw): Trade {
  return {
    id: t.id,
    stock: t.종목명,
    date: formatDate(t.거래일자),
    type: t.거래구분 === '매도' ? 'sell' : 'buy',
    price: t.거래단가.toLocaleString(),
    qty: t.거래수량,
    amount: t.거래금액.toLocaleString(),
    score: 0,
    deviation: 0,
  };
}

export function JournalPendingScreen() {
  const { isJournaled, getAllTrades, getAllAnalysis } = useAppState();
  const [trades, setTrades] = useState<TradeRaw[]>([]);
  const [analysis, setAnalysis] = useState<AnalysisResult[]>([]);
  const [type, setType] = useState<TypeFilter>('all');
  const [risk, setRisk] = useState<RiskFilter>('all');
  const [search, setSearch] = useState('');
  const [newest, setNewest] = useState(true);
  const [period, setPeriod] = useState(PERIODS[1]);
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
      return () => { cancelled = true; };
    }, [getAllTrades, getAllAnalysis])
  );

  const analysisLookup = useMemo(() => buildAnalysisLookup(analysis), [analysis]);

  // 일지 작성 대상 = 분석까지 정상적으로 끝난(매칭되는 분석 결과가 있는) 거래 중 아직
  // 일지를 안 쓴 것만 — 분석 안 된 거래는 위험도를 매길 수 없어 대상에서 제외한다.
  const pending = useMemo(
    () => trades
      .map((t) => ({ trade: t, match: findAnalysisForTrade(analysisLookup, t) }))
      .filter((x): x is { trade: TradeRaw; match: AnalysisResult } => x.match !== null)
      .filter((x) => !isJournaled(x.trade.id))
      .map(({ trade, match }) => ({ trade, risk: verdictToRisk(match.detail.verdict) })),
    [trades, analysisLookup, isJournaled]
  );

  const filtered = useMemo(() => {
    let list = pending.filter(({ trade: t, risk: r }) => {
      const tType = t.거래구분 === '매도' ? 'sell' : 'buy';
      if (type !== 'all' && tType !== type) return false;
      if (risk !== 'all' && r !== risk) return false;
      if (search && !t.종목명.includes(search)) return false;
      if (!isWithinPeriod(t.거래일자, period)) return false;
      return true;
    });
    if (!newest) list = [...list].reverse();
    return list;
  }, [pending, type, risk, search, newest, period]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const clampedPage = Math.min(page, totalPages - 1);
  const paginated = filtered.slice(clampedPage * PAGE_SIZE, (clampedPage + 1) * PAGE_SIZE);

  const updateFilter = <T,>(setter: (v: T) => void) => (v: T) => {
    setter(v);
    setPage(0);
  };

  return (
    <Screen back footer={<Pagination page={clampedPage} totalPages={totalPages} onChange={setPage} />}>
      <Text style={text.screenTitle}>기록되지 않은 거래</Text>
      <Text style={[text.screenSubtitle, styles.subtitle]}>원하는 거래를 골라 기록을 남겨보세요</Text>

      <View style={styles.filterRow}>
        <TypeTabs value={type} onChange={updateFilter(setType)} />
        <View style={styles.filterRight}>
          <SortToggle newest={newest} onToggle={() => { setNewest((v) => !v); setPage(0); }} />
          <PeriodDropdown value={period} onChange={(v) => { setPeriod(v); setPage(0); }} />
        </View>
      </View>
      <SearchInput value={search} onChangeText={updateFilter(setSearch)} placeholder="종목명 검색..." />
      <RiskChips value={risk} onChange={updateFilter(setRisk)} />

      {pending.length === 0 ? (
        <View style={styles.emptyWrap}>
          <Text style={styles.emptyText}>기록하지 않은 거래가 없어요</Text>
        </View>
      ) : paginated.length > 0 ? (
        <Card>
          {paginated.map(({ trade: t, risk: r }, i) => (
            <TradeRow
              key={t.id}
              trade={toTradeShape(t)}
              risk={r}
              index={i}
              onPress={() => goToJournalWrite(null, t.id)}
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
  emptyWrap: { paddingVertical: 40, alignItems: 'center' },
  emptyText: { fontSize: 15, color: '#64748b' },
});
