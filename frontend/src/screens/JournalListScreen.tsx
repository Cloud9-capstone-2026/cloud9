import React, { useMemo } from 'react';
import { View, Text, Pressable, StyleSheet } from 'react-native';
import { Screen } from '../components/Screen';
import { Card, CARD_PADDING } from '../components/Card';
import { GradientCard } from '../components/GradientCard';
import { EmptyState } from '../components/EmptyState';
import { JournalRow, JOURNAL_ROW_HEIGHT } from '../components/JournalRow';
import { RadarChart } from '../components/charts/RadarChart';
import { C, ACCENT, shadow, text } from '../theme/tokens';
import { emotionRadarData, tradesRaw } from '../data/mock';
import { useAppState } from '../state/AppState';
import { goToJournalFullList, goToJournalPending, goToJournalWrite } from '../navigation/navigationRef';

const RECENT_JOURNALS_VISIBLE = 5;

export function JournalListScreen() {
  const { journals, isJournaled, hasUploaded } = useAppState();
  const pendingCount = useMemo(
    () => (hasUploaded ? tradesRaw.filter((t) => !isJournaled(t.id)).length : 0),
    [isJournaled, hasUploaded]
  );
  const topTag = useMemo(() => {
    if (!hasUploaded) return null;
    const counts: Record<string, number> = {};
    journals.forEach((j) => { counts[j.emotion] = (counts[j.emotion] || 0) + 1; });
    let best: string | null = null;
    let bestCount = 0;
    Object.entries(counts).forEach(([k, c]) => { if (c > bestCount) { best = k; bestCount = c; } });
    return best ? { tag: best, count: bestCount } : null;
  }, [journals, hasUploaded]);

  return (
    <Screen contentStyle={styles.content}>
      <View>
        <Text style={text.screenTitle}>거래일지</Text>
        <Text style={[text.screenSubtitle, styles.subtitle]}>거래 이유와 감정을 기록하고 돌아봐요</Text>
      </View>

      <GradientCard colors={['#eff6ff', '#dbeafe']} style={[styles.banner, shadow.floating]}>
        <Text style={styles.bannerText}>
          {pendingCount > 0 ? `아직 ${pendingCount}건의 거래가 기록되지 않았어요` : '아직 업로드한 거래 내역이 없어요'}
        </Text>
        <Pressable onPress={goToJournalPending} disabled={pendingCount === 0}>
          <Text style={[styles.bannerCta, pendingCount === 0 && { color: '#a5b4c8' }]}>기록 추가하기 →</Text>
        </Pressable>
      </GradientCard>

      <View style={styles.grid}>
        <Card style={styles.radarCard}>
          <Text style={styles.radarTitle}>감정 태그 분석</Text>
          <View style={styles.radarWrap}>
            <RadarChart
              axes={emotionRadarData.map((d) => d.e)}
              series={hasUploaded ? [{ values: emotionRadarData.map((d) => d.value), color: ACCENT, fillOpacity: 0.28, width: 1.5 }] : []}
              size={165}
              radius={50}
              max={5}
              fontSize={8}
              height={160}
              dots={hasUploaded}
            />
          </View>
        </Card>
        <View style={styles.leftCol}>
          <Card style={styles.smallCard}>
            <Text style={styles.smallCardLabel}>총 거래일지</Text>
            <Text style={styles.smallCardValue}>
              {hasUploaded ? journals.length : '-'}
              <Text style={styles.smallCardUnit}>건</Text>
            </Text>
          </Card>
          <Card style={styles.smallCard}>
            <Text style={styles.smallCardLabel}>가장 잦은 태그</Text>
            <Text style={styles.tagValue}>{topTag ? `#${topTag.tag}` : '#-'}</Text>
            <Text style={styles.tagCount}>{topTag ? `${topTag.count}회` : '-회'}</Text>
          </Card>
        </View>
      </View>

      <View>
        <View style={styles.sectionHeaderRow}>
          <Text style={styles.sectionTitle}>최근 거래 일지</Text>
          <Pressable onPress={goToJournalFullList}>
            <Text style={styles.more}>더보기 &gt;</Text>
          </Pressable>
        </View>
        <Card style={!hasUploaded && styles.recentCardEmpty}>
          {hasUploaded ? (
            journals.slice(0, RECENT_JOURNALS_VISIBLE).map((j, i) => (
              <JournalRow key={j.id} journal={j} index={i} onPress={() => goToJournalWrite(j.id)} />
            ))
          ) : (
            <EmptyState
              title="아직 업로드한 거래 내역이 없어요"
              subtitle={'거래 내역을 업로드하면\n거래마다 일지를 기록할 수 있어요'}
            />
          )}
        </Card>
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  content: { gap: 24 },
  subtitle: { marginTop: 3 },
  banner: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingVertical: 22, paddingHorizontal: 18 },
  bannerText: { fontSize: 15, fontWeight: '500', color: C.navy, lineHeight: 20, flex: 1, marginRight: 8 },
  bannerCta: { fontSize: 14, fontWeight: '600', color: C.blue },
  grid: { flexDirection: 'row', gap: 13 },
  leftCol: { flex: 1, gap: 13 },
  smallCard: { flex: 1, minHeight: 100, justifyContent: 'center' },
  smallCardLabel: { fontSize: 13, color: C.navy, marginBottom: 7, lineHeight: 19 },
  smallCardValue: { fontSize: 27, fontWeight: '600', color: C.navy, letterSpacing: -0.5 },
  smallCardUnit: { fontSize: 15, fontWeight: '400', color: C.muted },
  tagValue: { fontSize: 19, fontWeight: '600', color: C.navy, letterSpacing: -0.2 },
  recentCardEmpty: { minHeight: JOURNAL_ROW_HEIGHT * RECENT_JOURNALS_VISIBLE + CARD_PADDING * 2, justifyContent: 'center' },
  tagCount: { fontSize: 13, color: C.muted, marginTop: 3 },
  radarCard: { flex: 1.15, padding: 14 },
  radarTitle: { fontSize: 13, fontWeight: '500', color: C.navy, marginBottom: 8 },
  radarWrap: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  sectionHeaderRow: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    paddingHorizontal: 2, marginBottom: 10,
  },
  sectionTitle: { fontSize: 20, fontWeight: '600', color: C.navy, letterSpacing: -0.1 },
  more: { fontSize: 13, color: C.muted },
});
