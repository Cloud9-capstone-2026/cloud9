import React, { useMemo, useState } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Screen } from '../components/Screen';
import { Card } from '../components/Card';
import { TradeRow } from '../components/TradeRow';
import { PeriodDropdown } from '../components/PeriodDropdown';
import { TypeTabs, SortToggle, SearchInput, RiskChips, Pagination, TypeFilter, RiskFilter } from '../components/FilterControls';
import { C, riskLevel, PERIODS, text } from '../theme/tokens';
import { tradesRaw } from '../data/mock';
import { useAppState } from '../state/AppState';
import { goToJournalWrite } from '../navigation/navigationRef';

const PAGE_SIZE = 10;

export function JournalPendingScreen() {
  const { isJournaled } = useAppState();
  const [type, setType] = useState<TypeFilter>('all');
  const [risk, setRisk] = useState<RiskFilter>('all');
  const [search, setSearch] = useState('');
  const [newest, setNewest] = useState(true);
  const [period, setPeriod] = useState(PERIODS[1]);
  const [page, setPage] = useState(0);
  const isDefaultFilter = type === 'all' && risk === 'all' && search === '';

  const pending = useMemo(() => tradesRaw.filter((t) => !isJournaled(t.id)), [isJournaled]);

  const filtered = useMemo(() => {
    let list = pending.filter((t) => {
      if (type !== 'all' && t.type !== type) return false;
      if (risk !== 'all' && riskLevel(t.score) !== risk) return false;
      if (search && !t.stock.includes(search)) return false;
      return true;
    });
    if (!newest) list = [...list].reverse();
    return list;
  }, [pending, type, risk, search, newest]);

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
          {paginated.map((t, i) => (
            <TradeRow key={t.id} trade={t} index={i} onPress={() => goToJournalWrite(null, t.id)} />
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
