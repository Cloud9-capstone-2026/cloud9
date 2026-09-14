import React, { useCallback, useMemo, useState } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { Screen } from '../components/Screen';
import { Card } from '../components/Card';
import { TradeRow } from '../components/TradeRow';
import { EmptyState } from '../components/EmptyState';
import { PeriodDropdown } from '../components/PeriodDropdown';
import { TypeTabs, SortToggle, SearchInput, RiskChips, Pagination, TypeFilter, RiskFilter } from '../components/FilterControls';
import { C, PERIODS, text } from '../theme/tokens';
import type { Trade } from '../data/types';
import type { TradeRaw } from '../api/trades';
import type { AnalysisResult } from '../api/analysis';
import { formatDate } from '../utils/formatDate';
import { isWithinPeriod } from '../utils/periodFilter';
import { buildAnalysisLookup, findAnalysisForTrade, verdictToRisk } from '../utils/matchTradeAnalysis';
import { goToReportDetail } from '../navigation/navigationRef';
import { useAppState } from '../state/AppState';

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

export function ReportListScreen() {
  const { getAllTrades, getAllAnalysis } = useAppState();
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
      return () => { cancelled = true; };
    }, [getAllTrades, getAllAnalysis])
  );

  const analysisLookup = useMemo(() => buildAnalysisLookup(analysis), [analysis]);

  // 분석까지 정상적으로 끝난(매칭되는 분석 결과가 있는) 거래만 보여준다 — 분석이 안 된
  // 거래는 백엔드의 알려진 job 실패 정리 버그로 인해 남아있는 것이라 사용자에게 노출하지 않는다.
  const withRisk = useMemo(
    () => trades
      .map((t) => ({ trade: t, match: findAnalysisForTrade(analysisLookup, t) }))
      .filter((x): x is { trade: TradeRaw; match: AnalysisResult } => x.match !== null)
      .map(({ trade, match }) => ({ trade, risk: verdictToRisk(match.detail.verdict) })),
    [trades, analysisLookup]
  );
  const hasData = withRisk.length > 0;

  const filtered = useMemo(() => {
    let list = withRisk.filter(({ trade: t, risk: r }) => {
      const tType = t.거래구분 === '매도' ? 'sell' : 'buy';
      if (type !== 'all' && tType !== type) return false;
      if (risk !== 'all' && r !== risk) return false;
      if (search && !t.종목명.includes(search)) return false;
      if (!isWithinPeriod(t.거래일자, period)) return false;
      return true;
    });
    // 서버가 이미 거래일자 내림차순으로 주므로 newest는 그대로, oldest만 뒤집는다.
    if (!newest) list = [...list].reverse();
    return list;
  }, [withRisk, type, risk, search, newest, period]);

  const totalPages = hasData ? Math.max(1, Math.ceil(filtered.length / PAGE_SIZE)) : 1;
  const clampedPage = Math.min(page, totalPages - 1);
  const paginated = filtered.slice(clampedPage * PAGE_SIZE, (clampedPage + 1) * PAGE_SIZE);

  const updateFilter = <T,>(setter: (v: T) => void) => (v: T) => {
    setter(v);
    setPage(0);
  };

  return (
    <Screen belowTabBar footer={<Pagination page={clampedPage} totalPages={totalPages} onChange={setPage} />}>
      <Text style={text.screenTitle}>분석 리포트</Text>
      <Text style={[text.screenSubtitle, styles.subtitle]}>분석하고 싶은 거래를 선택하세요</Text>

      <View style={styles.filterRow}>
        <TypeTabs value={type} onChange={updateFilter(setType)} />
        <View style={styles.filterRight}>
          <SortToggle newest={newest} onToggle={() => { setNewest((v) => !v); setPage(0); }} />
          <PeriodDropdown value={period} onChange={(v) => { setPeriod(v); setPage(0); }} />
        </View>
      </View>

      <SearchInput value={search} onChangeText={updateFilter(setSearch)} placeholder="종목명 검색..." />
      <RiskChips value={risk} onChange={updateFilter(setRisk)} />

      {!hasData ? (
        <EmptyState
          title="아직 업로드한 거래 내역이 없어요"
          subtitle={'거래내역을 업로드 하면\n거래별 분석 리포트가 생성돼요'}
        />
      ) : paginated.length > 0 ? (
        <Card>
          {paginated.map(({ trade: t, risk: r }, i) => (
            <TradeRow key={t.id} trade={toTradeShape(t)} index={i} risk={r} onPress={() => goToReportDetail(t.id)} />
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
