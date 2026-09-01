import React, { useMemo, useState } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Screen } from '../components/Screen';
import { Card } from '../components/Card';
import { NewsRow } from '../components/NewsRow';
import { PeriodDropdown } from '../components/PeriodDropdown';
import { Pagination } from '../components/FilterControls';
import { C, PERIODS } from '../theme/tokens';
import { dartNews } from '../data/mock';

const PAGE_SIZE = 10;

export function NewsFullListScreen() {
  const [period, setPeriod] = useState(PERIODS[1]);
  const [page, setPage] = useState(0);

  const totalPages = Math.max(1, Math.ceil(dartNews.length / PAGE_SIZE));
  const paginated = useMemo(
    () => dartNews.slice(page * PAGE_SIZE, page * PAGE_SIZE + PAGE_SIZE),
    [page]
  );

  return (
    <Screen back footer={<Pagination page={page} totalPages={totalPages} onChange={setPage} />}>
      <Text style={styles.title}>전체 소식</Text>
      <View style={styles.filterRow}>
        <PeriodDropdown value={period} onChange={(v) => { setPeriod(v); setPage(0); }} />
      </View>
      <Card>
        {paginated.map((n, i) => (
          <NewsRow key={n.id} news={n} index={i} />
        ))}
      </Card>
    </Screen>
  );
}

const styles = StyleSheet.create({
  title: { fontSize: 22, fontWeight: '600', color: C.navy, letterSpacing: -0.3 },
  filterRow: { flexDirection: 'row', justifyContent: 'flex-end', marginTop: 20, marginBottom: 13 },
});
