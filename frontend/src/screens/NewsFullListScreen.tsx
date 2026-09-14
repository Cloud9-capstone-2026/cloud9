import React, { useCallback, useMemo, useState } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { Screen } from '../components/Screen';
import { Card } from '../components/Card';
import { NewsRow } from '../components/NewsRow';
import { PeriodDropdown } from '../components/PeriodDropdown';
import { Pagination } from '../components/FilterControls';
import { PERIODS, text } from '../theme/tokens';
import type { DartNews } from '../data/types';
import { formatDate } from '../utils/formatDate';
import { useAppState } from '../state/AppState';

const PAGE_SIZE = 10;

export function NewsFullListScreen() {
  const { getAllNews } = useAppState();
  const [period, setPeriod] = useState(PERIODS[3]);
  const [page, setPage] = useState(0);
  const [news, setNews] = useState<DartNews[]>([]);

  useFocusEffect(
    useCallback(() => {
      let cancelled = false;
      (async () => {
        try {
          const res = await getAllNews(period);
          if (!cancelled) setNews(res.map((n) => ({ ...n, date: formatDate(n.date) })));
        } catch {
          // 네트워크 실패 시 기존 값 유지
        }
      })();
      return () => { cancelled = true; };
    }, [getAllNews, period])
  );

  const totalPages = Math.max(1, Math.ceil(news.length / PAGE_SIZE));
  const paginated = useMemo(
    () => news.slice(page * PAGE_SIZE, page * PAGE_SIZE + PAGE_SIZE),
    [news, page]
  );

  return (
    <Screen back footer={<Pagination page={page} totalPages={totalPages} onChange={setPage} />}>
      <Text style={text.screenTitle}>전체 공시·뉴스</Text>
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
  filterRow: { flexDirection: 'row', justifyContent: 'flex-end', marginTop: 20, marginBottom: 13 },
});
