import React, { useMemo, useState } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Screen } from '../components/Screen';
import { Card } from '../components/Card';
import { EmptyState } from '../components/EmptyState';
import { PeriodDropdown } from '../components/PeriodDropdown';
import { Pagination } from '../components/FilterControls';
import { C, PERIODS, text } from '../theme/tokens';
import { uploadHistoryRaw } from '../data/mock';
import { useAppState } from '../state/AppState';

const PAGE_SIZE = 10;

export function UploadHistoryScreen() {
  const { hasUploaded } = useAppState();
  const [period, setPeriod] = useState(PERIODS[1]);
  const [page, setPage] = useState(0);

  const totalPages = hasUploaded ? Math.max(1, Math.ceil(uploadHistoryRaw.length / PAGE_SIZE)) : 1;
  const pageItems = useMemo(
    () => (hasUploaded ? uploadHistoryRaw.slice(page * PAGE_SIZE, page * PAGE_SIZE + PAGE_SIZE) : []),
    [page, hasUploaded]
  );

  return (
    <Screen back footer={<Pagination page={page} totalPages={totalPages} onChange={setPage} />}>
      <Text style={text.screenTitle}>업로드 히스토리</Text>
      <Text style={[text.screenSubtitle, styles.subtitle]}>그동안 올린 파일과 분석 건수를 확인해요</Text>

      <View style={styles.filterRow}>
        <PeriodDropdown value={period} onChange={(v) => { setPeriod(v); setPage(0); }} />
      </View>

      {!hasUploaded ? (
        <EmptyState title="아직 업로드한 파일이 없어요" />
      ) : (
        <Card>
          {pageItems.map((u, i) => (
            <View key={u.id} style={[styles.row, i > 0 && styles.divider]}>
              <View style={{ flex: 1, minWidth: 0, paddingRight: 10 }}>
                <Text style={styles.filename} numberOfLines={1}>{u.filename}</Text>
                <Text style={styles.date}>{u.date}</Text>
              </View>
              <Text style={styles.count}>{u.count}건</Text>
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
