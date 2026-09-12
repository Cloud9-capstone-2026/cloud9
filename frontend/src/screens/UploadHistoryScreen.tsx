import React, { useCallback, useMemo, useState } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { Screen } from '../components/Screen';
import { Card } from '../components/Card';
import { EmptyState } from '../components/EmptyState';
import { PeriodDropdown } from '../components/PeriodDropdown';
import { Pagination } from '../components/FilterControls';
import { C, PERIODS, text } from '../theme/tokens';
import { formatDate } from '../utils/formatDate';
import type { UploadHistoryItem } from '../api/trades';
import { useAppState } from '../state/AppState';

const PAGE_SIZE = 10;

export function UploadHistoryScreen() {
  const { getUploads } = useAppState();
  const [period, setPeriod] = useState(PERIODS[1]);
  const [page, setPage] = useState(0);
  const [uploads, setUploads] = useState<UploadHistoryItem[]>([]);

  useFocusEffect(
    useCallback(() => {
      let cancelled = false;
      getUploads(200, 0).then((res) => { if (!cancelled) setUploads(res); }).catch(() => {});
      return () => { cancelled = true; };
    }, [getUploads])
  );

  const hasUploads = uploads.length > 0;
  const totalPages = Math.max(1, Math.ceil(uploads.length / PAGE_SIZE));
  const pageItems = useMemo(
    () => uploads.slice(page * PAGE_SIZE, page * PAGE_SIZE + PAGE_SIZE),
    [page, uploads]
  );

  return (
    <Screen back footer={<Pagination page={page} totalPages={totalPages} onChange={setPage} />}>
      <Text style={text.screenTitle}>업로드 히스토리</Text>
      <Text style={[text.screenSubtitle, styles.subtitle]}>그동안 올린 파일과 분석 건수를 확인해요</Text>

      <View style={styles.filterRow}>
        <PeriodDropdown value={period} onChange={(v) => { setPeriod(v); setPage(0); }} />
      </View>

      {!hasUploads ? (
        <EmptyState title="아직 업로드한 파일이 없어요" />
      ) : (
        <Card>
          {pageItems.map((u, i) => (
            <View key={u.id} style={[styles.row, i > 0 && styles.divider]}>
              <View style={{ flex: 1, minWidth: 0, paddingRight: 10 }}>
                <Text style={styles.filename} numberOfLines={1}>{u.file_name}</Text>
                <Text style={styles.date}>{formatDate(u.uploaded_at)}</Text>
              </View>
              {u.row_count != null ? (
                <Text style={styles.count}>{u.row_count}건</Text>
              ) : u.status === 'failed' ? (
                <Text style={[styles.count, { color: '#dc2626' }]}>분석 실패</Text>
              ) : (
                <Text style={[styles.count, { color: C.muted }]}>분석 중</Text>
              )}
            </View>
          ))}
        </Card>
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  subtitle: { marginTop: 3 },
  filterRow: { flexDirection: 'row', justifyContent: 'flex-end', marginTop: 26, marginBottom: 13 },
  row: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingVertical: 13 },
  divider: { borderTopWidth: 1, borderTopColor: C.border },
  filename: { fontSize: 15, fontWeight: '500', color: C.navy },
  date: { fontSize: 12, color: C.muted, marginTop: 3 },
  count: { fontSize: 16, fontWeight: '600', color: C.navy, flexShrink: 0 },
});
