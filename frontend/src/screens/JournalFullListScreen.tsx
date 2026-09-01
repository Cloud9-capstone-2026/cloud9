import React, { useMemo, useState } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Screen } from '../components/Screen';
import { Card } from '../components/Card';
import { JournalRow } from '../components/JournalRow';
import { PeriodDropdown } from '../components/PeriodDropdown';
import { TypeTabs, SortToggle, SearchInput, RiskChips, Pagination, TypeFilter, RiskFilter } from '../components/FilterControls';
import { C, PERIODS } from '../theme/tokens';
import { useAppState } from '../state/AppState';
import { goToJournalWrite } from '../navigation/navigationRef';

const PAGE_SIZE = 10;

export function JournalFullListScreen() {
  const { journals } = useAppState();
  const [type, setType] = useState<TypeFilter>('all');
  const [risk, setRisk] = useState<RiskFilter>('all');
  const [search, setSearch] = useState('');
  const [newest, setNewest] = useState(true);
  const [period, setPeriod] = useState(PERIODS[1]);
  const [page, setPage] = useState(0);
  const isDefaultFilter = type === 'all' && risk === 'all' && search === '';

  const filtered = useMemo(() => {
    let list = journals.filter((j) => {
      if (type !== 'all' && j.type !== type) return false;
      if (risk !== 'all' && j.risk !== risk) return false;
      if (search && !j.stock.includes(search) && !j.emotion.includes(search)) return false;
      return true;
    });
    if (!newest) list = [...list].reverse();
    return list;
  }, [journals, type, risk, search, newest]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const clampedPage = Math.min(page, totalPages - 1);
  const paginated = filtered.slice(clampedPage * PAGE_SIZE, (clampedPage + 1) * PAGE_SIZE);

  const updateFilter = <T,>(setter: (v: T) => void) => (v: T) => {
    setter(v);
    setPage(0);
  };

  return (
    <Screen back footer={<Pagination page={clampedPage} totalPages={totalPages} onChange={setPage} />}>
      <Text style={styles.title}>전체 거래일지</Text>
      <Text style={styles.subtitle}>기록된 모든 거래를 확인해요</Text>

      <View style={styles.filterRow}>
        <TypeTabs value={type} onChange={updateFilter(setType)} />
        <View style={styles.filterRight}>
          <SortToggle newest={newest} onToggle={() => { setNewest((v) => !v); setPage(0); }} />
          <PeriodDropdown value={period} onChange={(v) => { setPeriod(v); setPage(0); }} />
        </View>
      </View>

      <SearchInput value={search} onChangeText={updateFilter(setSearch)} placeholder="종목명 또는 태그 검색..." />
      <RiskChips value={risk} onChange={updateFilter(setRisk)} />

      {journals.length === 0 ? (
        <View style={styles.emptyWrap}>
          <Text style={styles.emptyTitle}>아직 업로드한 거래 내역이 없어요</Text>
          <Text style={styles.emptySub}>{'거래 내역을 업로드하면\n거래마다 일지를 기록할 수 있어요'}</Text>
        </View>
      ) : paginated.length > 0 ? (
        <Card>
          {paginated.map((j, i) => (
            <JournalRow key={j.id} journal={j} index={i} onPress={() => goToJournalWrite(j.id)} />
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
  emptyWrap: { alignItems: 'center', paddingVertical: 44, paddingHorizontal: 8 },
  emptyTitle: { fontSize: 16, color: C.navy, fontWeight: '500', marginBottom: 8 },
  emptySub: { fontSize: 13, color: C.muted, textAlign: 'center', lineHeight: 19 },
});
