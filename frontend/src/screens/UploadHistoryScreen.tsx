import React, { useMemo, useState } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Screen } from '../components/Screen';
import { Card } from '../components/Card';
import { PeriodDropdown } from '../components/PeriodDropdown';
import { Pagination } from '../components/FilterControls';
import { C, PERIODS } from '../theme/tokens';
import { uploadHistoryRaw } from '../data/mock';

const PAGE_SIZE = 10;

export function UploadHistoryScreen() {
  const [period, setPeriod] = useState(PERIODS[1]);
  const [page, setPage] = useState(0);

  const totalPages = Math.max(1, Math.ceil(uploadHistoryRaw.length / PAGE_SIZE));
  const pageItems = useMemo(
    () => uploadHistoryRaw.slice(page * PAGE_SIZE, page * PAGE_SIZE + PAGE_SIZE),
    [page]
  );

  return (
    <Screen back footer={<Pagination page={page} totalPages={totalPages} onChange={setPage} />}>
      <Text style={styles.title}>업로드 히스토리</Text>
      <Text style={styles.subtitle}>그동안 올린 파일과 분석 건수를 확인해요</Text>

      <View style={styles.filterRow}>
        <PeriodDropdown value={period} onChange={(v) => { setPeriod(v); setPage(0); }} />
      </View>

      {uploadHistoryRaw.length === 0 ? (
        <View style={styles.emptyWrap}>
          <Text style={styles.emptyText}>아직 업로드한 파일이 없어요</Text>
        </View>
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
  title: { fontSize: 22, fontWeight: '600', color: C.navy, letterSpacing: -0.3 },
  subtitle: { fontSize: 15, color: C.muted, marginTop: 3 },
  filterRow: { flexDirection: 'row', justifyContent: 'flex-end', marginTop: 26, marginBottom: 13 },
  row: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingVertical: 13 },
  divider: { borderTopWidth: 1, borderTopColor: C.border },
  filename: { fontSize: 15, fontWeight: '500', color: C.navy },
  date: { fontSize: 12, color: C.muted, marginTop: 3 },
  count: { fontSize: 16, fontWeight: '600', color: C.navy, flexShrink: 0 },
  emptyWrap: { paddingVertical: 60, alignItems: 'center' },
  emptyText: { fontSize: 15, color: '#64748b' },
});
