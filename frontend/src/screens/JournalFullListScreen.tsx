import React, { useMemo, useState } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Screen } from '../components/Screen';
import { Card } from '../components/Card';
import { JournalRow } from '../components/JournalRow';
import { TypeTabs, SortToggle, SearchInput, RiskChips, TypeFilter, RiskFilter } from '../components/FilterControls';
import { C } from '../theme/tokens';
import { useAppState } from '../state/AppState';
import { goToJournalWrite } from '../navigation/navigationRef';

export function JournalFullListScreen() {
  const { journals } = useAppState();
  const [type, setType] = useState<TypeFilter>('all');
  const [risk, setRisk] = useState<RiskFilter>('all');
  const [search, setSearch] = useState('');
  const [newest, setNewest] = useState(true);

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

  return (
    <Screen back>
      <Text style={styles.title}>전체 거래일지</Text>
      <Text style={styles.subtitle}>기록된 모든 거래를 확인해요</Text>

      <View style={styles.filterRow}>
        <TypeTabs value={type} onChange={setType} />
        <SortToggle newest={newest} onToggle={() => setNewest((v) => !v)} />
      </View>

      <SearchInput value={search} onChangeText={setSearch} placeholder="종목명 또는 태그 검색..." />
      <RiskChips value={risk} onChange={setRisk} />

      {filtered.length > 0 ? (
        <Card>
          {filtered.map((j, i) => (
            <JournalRow key={j.id} journal={j} index={i} onPress={() => goToJournalWrite(j.id)} />
          ))}
        </Card>
      ) : (
        <Text style={styles.empty}>검색 결과가 없습니다.</Text>
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  title: { fontSize: 20, fontWeight: '600', color: C.navy, letterSpacing: -0.3, lineHeight: 28 },
  subtitle: { fontSize: 13, color: C.muted, marginTop: 3, marginBottom: 16, lineHeight: 20 },
  filterRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 13 },
  empty: { textAlign: 'center', paddingVertical: 40, color: C.muted, fontSize: 14 },
});
