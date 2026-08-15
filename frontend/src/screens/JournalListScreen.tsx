import React from 'react';
import { View, Text, Pressable, StyleSheet } from 'react-native';
import { Screen } from '../components/Screen';
import { Card } from '../components/Card';
import { GradientCard } from '../components/GradientCard';
import { JournalRow } from '../components/JournalRow';
import { RadarChart } from '../components/charts/RadarChart';
import { C, ACCENT, shadow } from '../theme/tokens';
import { emotionRadarData } from '../data/mock';
import { useAppState } from '../state/AppState';
import { goToJournalFullList, goToJournalWrite } from '../navigation/navigationRef';

export function JournalListScreen() {
  const { journals } = useAppState();

  return (
    <Screen contentStyle={styles.content}>
      <View>
        <Text style={styles.title}>거래일지</Text>
        <Text style={styles.subtitle}>거래 이유와 감정을 기록하고 돌아봐요</Text>
      </View>

      <GradientCard colors={['#eff6ff', '#dbeafe']} style={[styles.banner, shadow.floating]}>
        <Text style={styles.bannerText}>아직 21건의 거래가 기록되지 않았어요</Text>
        <Pressable onPress={() => goToJournalWrite(null)}>
          <Text style={styles.bannerCta}>기록 추가하기 →</Text>
        </Pressable>
      </GradientCard>

      <View style={styles.grid}>
        <Card style={styles.radarCard}>
          <Text style={styles.radarTitle}>감정 태그 분석</Text>
          <View style={styles.radarWrap}>
            <RadarChart
              axes={emotionRadarData.map((d) => d.e)}
              series={[{ values: emotionRadarData.map((d) => d.value), color: ACCENT, fillOpacity: 0.28, width: 1.5 }]}
              size={165}
              radius={50}
              max={5}
              fontSize={8}
              height={160}
              dots
            />
          </View>
        </Card>
        <View style={styles.leftCol}>
          <Card style={styles.smallCard}>
            <Text style={styles.smallCardLabel}>총 거래일지</Text>
            <Text style={styles.smallCardValue}>4<Text style={styles.smallCardUnit}>건</Text></Text>
          </Card>
          <Card style={styles.smallCard}>
            <Text style={styles.smallCardLabel}>가장 잦은 태그</Text>
            <Text style={styles.tagValue}>#조급함</Text>
            <Text style={styles.tagCount}>4회</Text>
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
        <Card>
          {journals.slice(0, 5).map((j, i) => (
            <JournalRow key={j.id} journal={j} index={i} onPress={() => goToJournalWrite(j.id)} />
          ))}
        </Card>
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  content: { gap: 24 },
  title: { fontSize: 20, fontWeight: '600', color: C.navy, letterSpacing: -0.3, lineHeight: 28 },
  subtitle: { fontSize: 13, color: C.muted, marginTop: 3, lineHeight: 20 },
  banner: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingVertical: 16, paddingHorizontal: 18 },
  bannerText: { fontSize: 14, fontWeight: '500', color: C.navy, lineHeight: 21, flex: 1, marginRight: 8 },
  bannerCta: { fontSize: 13, fontWeight: '600', color: C.blue },
  grid: { flexDirection: 'row', gap: 13 },
  leftCol: { flex: 1, gap: 13 },
  smallCard: { flex: 1, minHeight: 100, justifyContent: 'center' },
  smallCardLabel: { fontSize: 12, color: C.navy, marginBottom: 7, lineHeight: 19 },
  smallCardValue: { fontSize: 24, fontWeight: '600', color: C.navy, letterSpacing: -0.5 },
  smallCardUnit: { fontSize: 13, fontWeight: '400', color: C.muted },
  tagValue: { fontSize: 17, fontWeight: '600', color: C.navy, letterSpacing: -0.2 },
  tagCount: { fontSize: 12, color: C.muted, marginTop: 3 },
  radarCard: { flex: 1.15, padding: 14 },
  radarTitle: { fontSize: 12, fontWeight: '500', color: C.navy, marginBottom: 8 },
  radarWrap: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  sectionHeaderRow: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    paddingHorizontal: 2, marginBottom: 10,
  },
  sectionTitle: { fontSize: 18, fontWeight: '600', color: C.navy, letterSpacing: -0.1 },
  more: { fontSize: 12, color: C.muted },
});
