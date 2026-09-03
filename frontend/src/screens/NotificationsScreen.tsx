import React, { useMemo, useState } from 'react';
import { View, Text, Pressable, StyleSheet } from 'react-native';
import Svg, { Path } from 'react-native-svg';
import { Screen } from '../components/Screen';
import { Card } from '../components/Card';
import { PeriodDropdown } from '../components/PeriodDropdown';
import { Pagination } from '../components/FilterControls';
import { NotifDetailModal } from '../components/NotifDetailModal';
import { IconChart } from '../assets/icons';
import { C, PERIODS, text } from '../theme/tokens';
import { NOTIFS } from '../data/mock';
import { useAppState } from '../state/AppState';

const PAGE_SIZE = 10;

function notifCopy(n: (typeof NOTIFS)[number]) {
  if (n.kind === 'analysis') return { title: '분석이 완료되었어요', body: `${n.file} 파일의 ${n.count}건의 거래 분석을 완료했어요.` };
  if (n.kind === 'upload') return { title: '업로드가 완료되었어요', body: `${n.file} 파일을 업로드 했어요.` };
  if (n.kind === 'uploadFail') return { title: '업로드에 실패했어요', body: `${n.file} 파일을 다시 올려주세요.` };
  return { title: '분석에 실패했어요', body: `${n.file} 파일을 분석하지 못했어요. 다시 시도해주세요.` };
}

function NotifIcon({ kind }: { kind: string }) {
  if (kind === 'uploadFail' || kind === 'analyzeFail') {
    return <Text style={{ fontSize: 18, color: '#dc2626', fontWeight: '700' }}>!</Text>;
  }
  if (kind === 'upload') {
    return (
      <Svg width={17} height={17} viewBox="0 0 24 24" fill="none">
        <Path d="M12 16V4m0 0L7 9m5-5l5 5" stroke={C.blue} strokeWidth={1.9} strokeLinecap="round" strokeLinejoin="round" />
        <Path d="M4 17v2a2 2 0 002 2h12a2 2 0 002-2v-2" stroke={C.blue} strokeWidth={1.9} strokeLinecap="round" />
      </Svg>
    );
  }
  return <IconChart active size={17} />;
}

export function NotificationsScreen() {
  const { notifRead, markNotifRead, markAllNotifRead } = useAppState();
  const [period, setPeriod] = useState(PERIODS[1]);
  const [page, setPage] = useState(0);
  const [openIdx, setOpenIdx] = useState<number | null>(null);

  const totalPages = Math.max(1, Math.ceil(NOTIFS.length / PAGE_SIZE));
  const pageItems = useMemo(() => {
    const start = page * PAGE_SIZE;
    return NOTIFS.slice(start, start + PAGE_SIZE).map((n, i) => ({ n, idx: start + i }));
  }, [page]);

  return (
    <Screen back footer={<Pagination page={page} totalPages={totalPages} onChange={setPage} />}>
      <Text style={text.screenTitle}>알림</Text>
      <View style={styles.subtitleRow}>
        <Text style={text.screenSubtitle}>업로드와 분석 상태를 알려드려요</Text>
        <Pressable onPress={markAllNotifRead}>
          <Text style={styles.markAll}>모두 읽음</Text>
        </Pressable>
      </View>

      <View style={styles.filterRow}>
        <PeriodDropdown value={period} onChange={(v) => { setPeriod(v); setPage(0); }} />
      </View>

      {NOTIFS.length === 0 ? (
        <View style={styles.emptyWrap}>
          <Text style={styles.emptyText}>아직 받은 알림이 없어요</Text>
        </View>
      ) : (
        <Card style={styles.card}>
          {pageItems.map(({ n, idx }, i) => {
            const copy = notifCopy(n);
            const unread = !notifRead[idx];
            const failKind = n.kind === 'uploadFail' || n.kind === 'analyzeFail';
            return (
              <Pressable
                key={idx}
                onPress={() => { markNotifRead(idx); setOpenIdx(idx); }}
                style={[styles.row, i > 0 && styles.rowDivider]}
              >
                <View style={[styles.iconBox, { backgroundColor: failKind ? '#fee2e2' : '#e8f0ff' }]}>
                  <NotifIcon kind={n.kind} />
                </View>
                <View style={{ flex: 1, minWidth: 0 }}>
                  <Text style={{ fontSize: 15, color: C.navy, fontWeight: unread ? '600' : '500' }} numberOfLines={1}>
                    {copy.title}
                  </Text>
                  <Text style={styles.body} numberOfLines={1}>{copy.body}</Text>
                  <Text style={styles.time}>{n.time}</Text>
                </View>
                {unread && <View style={styles.dot} />}
              </Pressable>
            );
          })}
        </Card>
      )}

      {openIdx !== null && (
        <NotifDetailModal
          visible
          iconBg={NOTIFS[openIdx].kind === 'uploadFail' || NOTIFS[openIdx].kind === 'analyzeFail' ? '#fee2e2' : '#e8f0ff'}
          icon={<NotifIcon kind={NOTIFS[openIdx].kind} />}
          title={notifCopy(NOTIFS[openIdx]).title}
          body={notifCopy(NOTIFS[openIdx]).body}
          time={NOTIFS[openIdx].time}
          onClose={() => setOpenIdx(null)}
        />
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  subtitleRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginTop: 3 },
  markAll: { fontSize: 13, fontWeight: '500', color: C.blue },
  filterRow: { flexDirection: 'row', justifyContent: 'flex-end', marginTop: 26, marginBottom: 13 },
  card: { paddingVertical: 4 },
  row: { flexDirection: 'row', alignItems: 'center', gap: 12, height: 92, paddingVertical: 14 },
  rowDivider: { borderTopWidth: 1, borderTopColor: C.border },
  iconBox: { width: 34, height: 34, borderRadius: 12, alignItems: 'center', justifyContent: 'center' },
  body: { fontSize: 13, color: C.muted, marginTop: 2 },
  time: { fontSize: 12, color: '#cbd5e1', marginTop: 3 },
  dot: { width: 7, height: 7, borderRadius: 4, backgroundColor: '#FACC15' },
  emptyWrap: { paddingVertical: 60, alignItems: 'center', paddingBottom: 60 },
  emptyText: { fontSize: 15, color: '#64748b' },
});
