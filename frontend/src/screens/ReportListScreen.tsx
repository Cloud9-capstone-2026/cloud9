import React, { useMemo, useState } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Screen } from '../components/Screen';
import { Card } from '../components/Card';
import { TradeRow } from '../components/TradeRow';
import { PeriodDropdown } from '../components/PeriodDropdown';
import { TypeTabs, SortToggle, SearchInput, RiskChips, Pagination, TypeFilter, RiskFilter } from '../components/FilterControls';
import { C, riskLevel, PERIODS } from '../theme/tokens';
import { tradesRaw } from '../data/mock';
import { goToReportDetail } from '../navigation/navigationRef';

const PAGE_SIZE = 10;

export function ReportListScreen() {
  const [type, setType] = useState<TypeFilter>('all');
  const [risk, setRisk] = useState<RiskFilter>('all');
  const [search, setSearch] = useState('');
  const [newest, setNewest] = useState(true);
  const [period, setPeriod] = useState(PERIODS[1]);
  const [page, setPage] = useState(0);
  const isDefaultFilter = type === 'all' && risk === 'all' && search === '';

  const filtered = useMemo(() => {
    let list = tradesRaw.filter((t) => {
      if (type !== 'all' && t.type !== type) return false;
      if (risk !== 'all' && riskLevel(t.score) !== risk) return false;
      if (search && !t.stock.includes(search)) return false;
      return true;
    });
    if (!newest) list = [...list].reverse();
    return list;
  }, [type, risk, search, newest]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const clampedPage = Math.min(page, totalPages - 1);
  const paginated = filtered.slice(clampedPage * PAGE_SIZE, (clampedPage + 1) * PAGE_SIZE);

  const updateFilter = <T,>(setter: (v: T) => void) => (v: T) => {
    setter(v);
    setPage(0);
  };

  return (
    <Screen footer={<Pagination page={clampedPage} totalPages={totalPages} onChange={setPage} />}>
      <Text style={styles.title}>분석 리포트</Text>
      <Text style={styles.subtitle}>분석하고 싶은 거래를 선택하세요</Text>

      <View style={styles.filterRow}>
        <TypeTabs value={type} onChange={updateFilter(setType)} />
        <View style={styles.filterRight}>
          <SortToggle newest={newest} onToggle={() => { setNewest((v) => !v); setPage(0); }} />
          <PeriodDropdown value={period} onChange={(v) => { setPeriod(v); setPage(0); }} />
        </View>
      </View>

      <SearchInput value={search} onChangeText={updateFilter(setSearch)} placeholder="종목명 검색..." />
      <RiskChips value={risk} onChange={updateFilter(setRisk)} />

      {paginated.length > 0 ? (
        <Card>
          {paginated.map((t, i) => (
            <TradeRow key={t.id} trade={t} index={i} onPress={() => goToReportDetail(t.id)} />
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
  title: { fontSize: 22, fontWeight: '600', color: C.navy, letterSpacing: -0.3, lineHeight: 28 },
  subtitle: { fontSize: 15, color: C.muted, marginTop: 3, marginBottom: 16, lineHeight: 20 },
  filterRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 13 },
  filterRight: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  empty: { textAlign: 'center', paddingVertical: 40, color: C.muted, fontSize: 16 },
});
