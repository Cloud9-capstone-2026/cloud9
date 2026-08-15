import React from 'react';
import { View, Text, Pressable, StyleSheet } from 'react-native';
import { Screen } from '../components/Screen';
import { Card } from '../components/Card';
import { GradientCard } from '../components/GradientCard';
import { RadarChart } from '../components/charts/RadarChart';
import { TrendBarChart } from '../components/charts/TrendBarChart';
import { Avatar } from '../assets/Avatar';
import { C, ACCENT, shadow, BIAS_LABELS, BIAS_COLORS, BIAS_TREND_KEYS } from '../theme/tokens';
import { biasComparisonData, biasTrend, BIAS_SCORES } from '../data/mock';
import { goToDiagnosis } from '../navigation/navigationRef';

export function MyPageScreen() {
  return (
    <Screen contentStyle={styles.content}>
      <View>
        <Text style={styles.title}>성향분석</Text>
        <Text style={styles.subtitle}>내 투자 성향을 파악하고 거래 패턴을 분석해요</Text>
      </View>

      <GradientCard colors={['#eff6ff', '#dbeafe']} style={shadow.floating}>
        <View style={styles.bannerRow}>
          <View style={{ flex: 1 }}>
            <Text style={styles.bannerTitle}>내 투자 성향, 변하지는 않았을까요?</Text>
            <Text style={styles.bannerSub}>시간이 지나면서 성향은 달라질 수 있어요.{'\n'}궁금하다면 다시 검사해보세요.</Text>
          </View>
          <Pressable onPress={goToDiagnosis}>
            <Text style={styles.bannerCta}>다시 검사하기 →</Text>
          </Pressable>
        </View>
      </GradientCard>

      <View>
        <View style={styles.sectionHeaderRow}>
          <Text style={styles.sectionTitle}>나의 투자 성향</Text>
          <Text style={styles.updateDate}>최종 업데이트 2026.07.31</Text>
        </View>
        <Card>
          <Text style={styles.personaName}>불안한 동조자</Text>
          <View style={styles.personaRow}>
            <Avatar size={100} />
            <View style={styles.biasBars}>
              {BIAS_LABELS.map((label, i) => (
                <View key={label} style={styles.biasBarRow}>
                  <Text style={styles.biasLabel}>{label}</Text>
                  <View style={styles.biasTrack}>
                    <View style={[styles.biasFill, { width: `${BIAS_SCORES[i]}%`, backgroundColor: BIAS_COLORS[i] }]} />
                  </View>
                  <Text style={[styles.biasScore, { color: BIAS_COLORS[i] }]}>{BIAS_SCORES[i]}</Text>
                </View>
              ))}
            </View>
          </View>
        </Card>
      </View>

      <View>
        <Text style={styles.sectionTitleStandalone}>검사 vs 거래 성향 비교</Text>
        <Card>
          <View style={styles.compareRow}>
            <View style={{ flex: 1 }}>
              <RadarChart
                axes={biasComparisonData.map((d) => d.subject)}
                series={[
                  { values: biasComparisonData.map((d) => d.self), color: ACCENT, fillOpacity: 0.3, width: 2 },
                  { values: biasComparisonData.map((d) => d.trading), color: '#64748b', fillOpacity: 0.18, width: 2 },
                ]}
                size={190}
                radius={62}
                max={100}
                fontSize={10}
                height={190}
              />
            </View>
            <View style={styles.legendCol}>
              <View style={styles.legendItem}>
                <View style={[styles.legendDot, { backgroundColor: ACCENT }]} />
                <Text style={styles.legendText}>검사 결과</Text>
              </View>
              <View style={styles.legendItem}>
                <View style={[styles.legendDot, { backgroundColor: '#64748b' }]} />
                <Text style={styles.legendText}>거래 기반</Text>
              </View>
            </View>
          </View>
          <View style={styles.divider} />
          <Text style={styles.compareText}>
            처분효과가 거래 기반 대비 <Text style={styles.comparePlus}>+7p</Text> 높아요. 실제로 손절을 더 회피하는 경향이 보입니다.
          </Text>
        </Card>
      </View>

      <View>
        <Text style={styles.sectionTitleStandalone}>누적 통계</Text>
        <View style={styles.trendGrid}>
          {BIAS_TREND_KEYS.map((key, i) => {
            const latest = biasTrend[biasTrend.length - 1][key];
            return (
              <Card key={key} style={styles.trendCard}>
                <View style={styles.trendHeader}>
                  <Text style={styles.trendLabel}>{BIAS_LABELS[i]}</Text>
                  <Text style={[styles.trendValue, { color: BIAS_COLORS[i] }]}>
                    {latest}<Text style={styles.trendUnit}>/100</Text>
                  </Text>
                </View>
                <TrendBarChart data={biasTrend} dataKey={key} color={BIAS_COLORS[i]} />
              </Card>
            );
          })}
        </View>
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  content: { gap: 24 },
  title: { fontSize: 20, fontWeight: '600', color: C.navy, letterSpacing: -0.3, lineHeight: 28 },
  subtitle: { fontSize: 13, color: C.muted, marginTop: 3, lineHeight: 20 },
  bannerRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  bannerTitle: { fontSize: 14, fontWeight: '500', color: C.navy, lineHeight: 21 },
  bannerSub: { fontSize: 12, color: C.muted, marginTop: 4, lineHeight: 20 },
  bannerCta: { fontSize: 13, fontWeight: '600', color: C.blue, marginLeft: 8 },
  sectionHeaderRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: 2, marginBottom: 10 },
  sectionTitle: { fontSize: 18, fontWeight: '600', color: C.navy, letterSpacing: -0.1 },
  sectionTitleStandalone: { fontSize: 18, fontWeight: '600', color: C.navy, letterSpacing: -0.1, paddingHorizontal: 2, marginBottom: 10 },
  updateDate: { fontSize: 12, color: C.muted },
  personaName: { fontSize: 14, fontWeight: '500', color: C.navy, marginBottom: 14 },
  personaRow: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  biasBars: { flex: 1, gap: 8 },
  biasBarRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  biasLabel: { fontSize: 11, color: C.muted, width: 56 },
  biasTrack: { height: 5, backgroundColor: C.mutedBg, borderRadius: 999, overflow: 'hidden', flex: 1 },
  biasFill: { height: '100%', borderRadius: 999 },
  biasScore: { fontSize: 11, fontWeight: '500', width: 24, textAlign: 'right' },
  compareRow: { flexDirection: 'row', alignItems: 'center', gap: 16 },
  legendCol: { gap: 10 },
  legendItem: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  legendDot: { width: 10, height: 10, borderRadius: 2 },
  legendText: { fontSize: 12, color: C.navy, fontWeight: '500' },
  divider: { height: 1, backgroundColor: C.border, marginVertical: 12 },
  compareText: { fontSize: 13, color: C.navy, lineHeight: 22 },
  comparePlus: { color: '#AE77FF', fontWeight: '600' },
  trendGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 13 },
  trendCard: { width: '46%', flexGrow: 1, borderRadius: 26, padding: 10, paddingTop: 14 },
  trendHeader: { flexDirection: 'row', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: 8, paddingHorizontal: 4 },
  trendLabel: { fontSize: 12, fontWeight: '500', color: C.navy },
  trendValue: { fontSize: 15, fontWeight: '600' },
  trendUnit: { fontSize: 11, fontWeight: '400', color: C.muted },
});
