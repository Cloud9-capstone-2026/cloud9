import React, { useMemo, useState } from 'react';
import { View, Text, Pressable, StyleSheet } from 'react-native';
import { Screen } from '../components/Screen';
import { Card, CARD_PADDING } from '../components/Card';
import { EmptyState } from '../components/EmptyState';
import { TradeRow, TRADE_ROW_HEIGHT } from '../components/TradeRow';
import { NewsRow } from '../components/NewsRow';
import { RingChart } from '../components/charts/RingChart';
import { MonthlyBarChart, MONTHLY_CHART_HEIGHT } from '../components/charts/MonthlyBarChart';
import { Avatar } from '../assets/Avatar';
import { C, RISK, riskLevel, BIAS_LABELS, BIAS_COLORS, text } from '../theme/tokens';
import { tradesRaw, monthlyData, dartNews, BIAS_SCORES } from '../data/mock';
import { goToTab, goToNewsFullList, goToReportDetail } from '../navigation/navigationRef';
import { useAppState } from '../state/AppState';

const RECENT_TRADES_VISIBLE = 5;

export function HomeScreen() {
  const { openBiasInfo, hasUploaded } = useAppState();
  const [chartTab, setChartTab] = useState<'trades' | 'anomaly'>('trades');

  const counts = useMemo(() => {
    if (!hasUploaded) return { danger: 0, caution: 0, safe: 0 };
    let danger = 0, caution = 0, safe = 0;
    tradesRaw.forEach((t) => {
      const r = riskLevel(t.score);
      if (r === 'danger') danger++;
      else if (r === 'caution') caution++;
      else safe++;
    });
    return { danger, caution, safe };
  }, [hasUploaded]);

  return (
    <Screen contentStyle={styles.content}>
      <View>
        <Text style={text.screenTitle}>안녕하세요, 김투자님</Text>
        <Text style={[text.screenSubtitle, styles.lastUpload]}>
          {hasUploaded ? '마지막 업로드 2026.07.31' : '아직 업로드한 거래 내역이 없어요'}
        </Text>
      </View>

      <View>
        <View style={styles.sectionHeaderRow}>
          <Text style={styles.sectionTitle}>나의 투자 성향</Text>
          <Pressable onPress={() => goToTab('MyPage')}>
            <Text style={styles.more}>더보기 &gt;</Text>
          </Pressable>
        </View>
        <Card>
          <View style={styles.personaTitleRow}>
            <Text style={styles.personaName}>불안한 동조자</Text>
            <Pressable onPress={openBiasInfo} style={styles.infoBtn}>
              <Text style={styles.infoBtnText}>?</Text>
            </Pressable>
          </View>
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
        <View style={styles.sectionHeaderRow}>
          <Text style={styles.sectionTitle}>요약지표</Text>
        </View>
        <View style={styles.summaryGrid}>
          <View style={styles.summaryLeftCol}>
            <Card style={styles.summaryCardWide}>
              <Text style={styles.summaryCardWideTitle}>거래 분석 요약</Text>
              <RingChart
                danger={counts.danger}
                caution={counts.caution}
                safe={counts.safe}
                dangerColor={RISK.danger.ring}
                cautionColor={RISK.caution.ring}
                safeColor={RISK.safe.ring}
              />
              <View style={styles.legend}>
                {[
                  { label: '이상', color: RISK.danger.ring, text: hasUploaded ? `${counts.danger}건` : '-건' },
                  { label: '경고', color: RISK.caution.ring, text: hasUploaded ? `${counts.caution}건` : '-건' },
                  { label: '정상', color: RISK.safe.ring, text: hasUploaded ? `${counts.safe}건` : '-건' },
                ].map((r) => (
                  <View key={r.label} style={styles.legendRow}>
                    <View style={styles.legendLeft}>
                      <View style={[styles.legendDot, { backgroundColor: r.color }]} />
                      <Text style={styles.legendLabel}>{r.label}</Text>
                    </View>
                    <Text style={styles.legendValue}>{r.text}</Text>
                  </View>
                ))}
              </View>
            </Card>
          </View>
          <View style={styles.summaryRightCol}>
            <Card style={styles.summaryCard}>
              <Text style={styles.summaryLabel}>총 거래 내역</Text>
              <View style={styles.summaryValueRow}>
                <Text style={styles.summaryValue}>{hasUploaded ? 69 : '-'}</Text>
                <Text style={styles.summaryUnit}>건</Text>
              </View>
              <Text style={[styles.summaryDiff, { color: hasUploaded ? C.red : C.muted }]}>
                {hasUploaded ? '+ 12건' : '- 건'}
              </Text>
            </Card>
            <Card style={styles.summaryCard}>
              <Text style={styles.summaryLabel}>이상 탐지율</Text>
              <View style={styles.summaryValueRow}>
                <Text style={styles.summaryValue}>{hasUploaded ? 46.4 : '-'}</Text>
                <Text style={styles.summaryUnit}>%</Text>
              </View>
              <Text style={[styles.summaryDiff, { color: hasUploaded ? C.blue : C.muted }]}>
                {hasUploaded ? '- 2.1%' : '- %'}
              </Text>
            </Card>
          </View>
        </View>
      </View>

      <View>
        <View style={styles.chartTabRow}>
          {([
            ['trades', '월별 거래 내역'],
            ['anomaly', '이상 탐지 추이'],
          ] as const).map(([id, label]) => {
            const active = chartTab === id;
            return (
              <Pressable key={id} onPress={() => setChartTab(id)} style={[styles.chartTab, active && styles.chartTabActive]}>
                <Text style={{ fontSize: 16, fontWeight: active ? '600' : '400', color: active ? C.navy : C.muted }}>
                  {label}
                </Text>
              </Pressable>
            );
          })}
        </View>
        <Card style={[styles.chartCard, !hasUploaded && styles.chartCardEmpty]}>
          {hasUploaded ? (
            <MonthlyBarChart data={monthlyData} activeTab={chartTab} />
          ) : (
            <EmptyState title="아직 업로드한 거래 내역이 없어요" />
          )}
        </Card>
      </View>

      <View>
        <View style={styles.sectionHeaderRow}>
          <Text style={styles.sectionTitle}>오늘의 주요 소식</Text>
          <Pressable onPress={goToNewsFullList}>
            <Text style={styles.more}>더보기 &gt;</Text>
          </Pressable>
        </View>
        <Card>
          {dartNews.slice(0, 3).map((n, i) => (
            <NewsRow key={n.id} news={n} index={i} />
          ))}
        </Card>
      </View>

      <View>
        <View style={styles.sectionHeaderRow}>
          <Text style={styles.sectionTitle}>최근 거래 내역</Text>
          <Pressable onPress={() => goToTab('ReportList')}>
            <Text style={styles.more}>더보기 &gt;</Text>
          </Pressable>
        </View>
        <Card style={!hasUploaded && styles.recentTradesCardEmpty}>
          {hasUploaded ? (
            tradesRaw.slice(0, RECENT_TRADES_VISIBLE).map((t, i) => (
              <TradeRow key={t.id} trade={t} index={i} onPress={() => goToReportDetail(t.id)} />
            ))
          ) : (
            <EmptyState
              title="아직 업로드한 거래 내역이 없어요"
              subtitle={'거래내역을 업로드 하면\n거래별 분석 리포트가 생성돼요'}
            />
          )}
        </Card>
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  content: { gap: 24 },
  lastUpload: { marginTop: 3 },
  sectionHeaderRow: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    paddingHorizontal: 2, marginBottom: 10,
  },
  sectionTitle: { fontSize: 20, fontWeight: '600', color: C.navy, letterSpacing: -0.1 },
  more: { fontSize: 13, color: C.muted },
  personaTitleRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 },
  personaName: { fontSize: 16, fontWeight: '500', color: C.navy, letterSpacing: -0.1 },
  infoBtn: { width: 18, height: 18, borderRadius: 9, borderWidth: 1.3, borderColor: '#cbd5e1', alignItems: 'center', justifyContent: 'center' },
  infoBtnText: { fontSize: 12, fontWeight: '600', color: '#94a3b8' },
  personaRow: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  biasBars: { flex: 1, gap: 8 },
  biasBarRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  biasLabel: { fontSize: 12, color: C.muted, width: 56 },
  biasTrack: { height: 5, backgroundColor: C.mutedBg, borderRadius: 999, overflow: 'hidden', flex: 1 },
  biasFill: { height: '100%', borderRadius: 999 },
  biasScore: { fontSize: 12, fontWeight: '500', width: 24, textAlign: 'right' },
  summaryGrid: { flexDirection: 'row', gap: 13 },
  summaryLeftCol: { flex: 1.15 },
  summaryRightCol: { flex: 1, gap: 13 },
  summaryCard: { flex: 1 },
  summaryCardWide: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: 10 },
  summaryCardWideTitle: { fontSize: 13, fontWeight: '500', color: C.navy, alignSelf: 'flex-start' },
  summaryLabel: { fontSize: 13, color: C.navy, marginBottom: 7, lineHeight: 19 },
  summaryValueRow: { flexDirection: 'row', alignItems: 'baseline', gap: 2 },
  summaryValue: { fontSize: 29, fontWeight: '600', color: C.navy, letterSpacing: -0.5 },
  summaryUnit: { fontSize: 13, color: C.muted },
  summaryDiff: { fontSize: 13, fontWeight: '500', marginTop: 4 },
  legend: { gap: 6, alignSelf: 'stretch' },
  legendRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  legendLeft: { flexDirection: 'row', alignItems: 'center', gap: 5 },
  legendDot: { width: 8, height: 8, borderRadius: 2 },
  legendLabel: { fontSize: 12, color: C.muted },
  legendValue: { fontSize: 13, fontWeight: '500', color: C.navy },
  chartTabRow: { flexDirection: 'row', alignItems: 'center', gap: 20, paddingHorizontal: 2, marginBottom: 12 },
  chartTab: { paddingVertical: 5, paddingTop: 2, borderBottomWidth: 2, borderBottomColor: 'transparent' },
  chartTabActive: { borderBottomColor: C.navy },
  chartCard: { paddingHorizontal: 8, paddingTop: 16, paddingBottom: 10 },
  // 빈 상태에서도 카드 크기가 그대로 유지되도록, 새로 잰 값이 아니라
  // 원래 콘텐츠(차트/거래 로우)가 실제로 차지하는 높이를 그대로 계산해서 재사용.
  chartCardEmpty: { minHeight: MONTHLY_CHART_HEIGHT + 16 + 10, justifyContent: 'center' },
  recentTradesCardEmpty: { minHeight: TRADE_ROW_HEIGHT * RECENT_TRADES_VISIBLE + CARD_PADDING * 2, justifyContent: 'center' },
});
