import React, { useCallback, useMemo, useState } from 'react';
import { View, Text, Image, Pressable, StyleSheet } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { Screen } from '../components/Screen';
import { Card } from '../components/Card';
import { GradientCard } from '../components/GradientCard';
import { DumbbellChart } from '../components/charts/DumbbellChart';
import { TrendLineChart } from '../components/charts/TrendLineChart';
import { Avatar } from '../assets/Avatar';
import { C, ACCENT, shadow, BIAS_LABELS, BIAS_COLORS, BIAS_TREND_KEYS, BIAS_KEYS, text } from '../theme/tokens';
import { getCharacter } from '../constants/characterAssets';
import { buildBiasTrend } from '../utils/buildBiasTrend';
import { buildBiasComparison, computeTopBias } from '../utils/buildBiasComparison';
import { formatDate } from '../utils/formatDate';
import type { SurveyResult } from '../api/survey';
import type { AnalysisResult } from '../api/analysis';
import type { BiasComparisonDatum } from '../data/types';
import { goToDiagnosis } from '../navigation/navigationRef';
import { useAppState } from '../state/AppState';

// 검사도 거래도 없을 때 DumbbellChart의 그리드·라벨만 보여주기 위한 자리표시자(empty=true라 값은 안 쓰임).
const EMPTY_COMPARISON: BiasComparisonDatum[] = BIAS_TREND_KEYS.map((subject) => ({ subject, self: 0, trading: 0 }));

export function MyPageScreen() {
  const { openBiasInfo, getLatestSurvey, getSurveyHistory, getAllAnalysis } = useAppState();
  // undefined = 아직 조회 안 됨(로딩), null = 조회했지만 결과 없음(검사 이력 없음)
  const [latest, setLatest] = useState<SurveyResult | null | undefined>(undefined);
  const [history, setHistory] = useState<SurveyResult[]>([]);
  const [analysis, setAnalysis] = useState<AnalysisResult[]>([]);

  useFocusEffect(
    useCallback(() => {
      let cancelled = false;
      (async () => {
        try {
          const [latestRes, historyRes, analysisRes] = await Promise.all([
            getLatestSurvey(), getSurveyHistory(20), getAllAnalysis(),
          ]);
          if (!cancelled) {
            setLatest(latestRes);
            setHistory(historyRes);
            setAnalysis(analysisRes);
          }
        } catch {
          // 네트워크 실패 시 기존 값 유지 — 화면은 이전 상태(또는 빈 상태)로 남는다.
        }
      })();
      return () => { cancelled = true; };
    }, [getLatestSurvey, getSurveyHistory, getAllAnalysis])
  );

  const trend = useMemo(() => buildBiasTrend(history), [history]);
  const character = latest ? getCharacter(latest.type_code) : null;
  const hasAnalysis = analysis.length > 0;

  const topBias = useMemo(() => computeTopBias(analysis), [analysis]);
  const comparison = useMemo(() => buildBiasComparison(latest ?? null, analysis), [latest, analysis]);

  const insight = useMemo(() => {
    if (comparison.length === 0) return null;
    let best = comparison[0];
    let bestDiff = -1;
    comparison.forEach((d) => {
      const diff = Math.abs(d.trading - d.self);
      if (diff > bestDiff) { bestDiff = diff; best = d; }
    });
    return { subject: best.subject, diff: bestDiff, bigger: best.trading > best.self };
  }, [comparison]);

  return (
    <Screen contentStyle={styles.content}>
      <View>
        <Text style={text.screenTitle}>성향분석</Text>
        <Text style={[text.screenSubtitle, styles.subtitle]}>내 투자 성향을 파악하고 거래 패턴을 분석해요</Text>
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
          <Text style={styles.updateDate}>{latest ? `최종 업데이트 ${formatDate(latest.created_at)}` : ''}</Text>
        </View>
        <Card>
          <View style={styles.personaTitleRow}>
            <Text style={styles.personaName}>{character ? character.name : '검사 결과가 없어요'}</Text>
            <Pressable onPress={openBiasInfo} style={styles.infoBtn}>
              <Text style={styles.infoBtnText}>?</Text>
            </Pressable>
          </View>
          <View style={styles.personaRow}>
            {character?.image ? (
              <Image source={character.image} style={{ width: 100, height: 100, borderRadius: 50 }} />
            ) : (
              <Avatar size={100} />
            )}
            <View style={styles.biasBars}>
              {BIAS_LABELS.map((label, i) => {
                const score = latest ? Math.round(latest.scores[BIAS_KEYS[i]].normalized) : null;
                return (
                  <View key={label} style={styles.biasBarRow}>
                    <Text style={styles.biasLabel}>{label}</Text>
                    <View style={styles.biasTrack}>
                      <View style={[styles.biasFill, { width: `${score ?? 0}%`, backgroundColor: BIAS_COLORS[i] }]} />
                    </View>
                    <Text style={[styles.biasScore, { color: BIAS_COLORS[i] }]}>{score ?? '-'}</Text>
                  </View>
                );
              })}
            </View>
          </View>
        </Card>
      </View>

      <View>
        <Text style={styles.sectionTitleStandalone}>거래로 본 나의 성향</Text>
        <View style={{ gap: 13 }}>
          <Card style={styles.topBiasCard}>
            <Text style={styles.topBiasLabel}>거래에서 가장 많이 나타난 편향</Text>
            <View style={{ alignItems: 'flex-end' }}>
              <Text style={styles.topBiasTag}>{topBias ? `#${topBias.label}` : '#-'}</Text>
              <Text style={styles.topBiasCount}>{topBias ? `${topBias.count}회` : '-회'}</Text>
            </View>
          </Card>

          <Card>
            <Text style={styles.compareSubtitle}>검사 결과 vs 실제 거래 데이터</Text>
            <View style={styles.legendRow}>
              <View style={styles.legendItem}>
                <View style={[styles.legendDot, { backgroundColor: ACCENT }]} />
                <Text style={styles.legendText}>검사 결과</Text>
              </View>
              <View style={styles.legendItem}>
                <View style={[styles.legendDot, { backgroundColor: '#64748b' }]} />
                <Text style={styles.legendText}>실제 거래 데이터</Text>
              </View>
            </View>
            <View style={{ marginTop: 10 }}>
              <DumbbellChart data={comparison.length > 0 ? comparison : EMPTY_COMPARISON} empty={!hasAnalysis || !latest} />
            </View>
            {hasAnalysis && latest && insight && (
              <View style={styles.insightBlock}>
                <View style={styles.insightIconBox}>
                  <Text style={styles.insightIconText}>!</Text>
                </View>
                <Text style={styles.insightText}>
                  {insight.subject}이 실제 거래에서 <Text style={styles.insightNum}>{insight.diff}%</Text> {insight.bigger ? '더 크게' : '더 작게'} 나타나요.
                </Text>
              </View>
            )}
          </Card>
        </View>
      </View>

      <View>
        <Text style={styles.sectionTitleStandalone}>검사 히스토리</Text>
        <View style={styles.trendGrid}>
          {BIAS_TREND_KEYS.map((key, i) => {
            const lastRow = trend[trend.length - 1];
            const latestVal = lastRow ? lastRow[key] : null;
            return (
              <Card key={key} style={styles.trendCard}>
                <View style={styles.trendHeader}>
                  <Text style={styles.trendLabel}>{BIAS_LABELS[i]}</Text>
                  <Text style={[styles.trendValue, { color: BIAS_COLORS[i] }]}>
                    {latestVal ?? '-'}<Text style={styles.trendUnit}>/100</Text>
                  </Text>
                </View>
                <TrendLineChart data={trend} dataKey={key} color={BIAS_COLORS[i]} />
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
  subtitle: { marginTop: 3 },
  bannerRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  bannerTitle: { fontSize: 15, fontWeight: '500', color: C.navy, lineHeight: 20 },
  bannerSub: { fontSize: 13, color: C.muted, marginTop: 4, lineHeight: 20 },
  bannerCta: { fontSize: 14, fontWeight: '600', color: C.blue, marginLeft: 8 },
  sectionHeaderRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: 2, marginBottom: 10 },
  sectionTitle: { fontSize: 20, fontWeight: '600', color: C.navy, letterSpacing: -0.1 },
  sectionTitleStandalone: { fontSize: 20, fontWeight: '600', color: C.navy, letterSpacing: -0.1, paddingHorizontal: 2, marginBottom: 10 },
  updateDate: { fontSize: 13, color: C.muted },
  personaTitleRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 },
  personaName: { fontSize: 16, fontWeight: '500', color: C.navy },
  infoBtn: { width: 18, height: 18, borderRadius: 9, borderWidth: 1.3, borderColor: '#cbd5e1', alignItems: 'center', justifyContent: 'center' },
  infoBtnText: { fontSize: 12, fontWeight: '600', color: '#94a3b8' },
  personaRow: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  biasBars: { flex: 1, gap: 8 },
  biasBarRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  biasLabel: { fontSize: 12, color: C.muted, width: 56 },
  biasTrack: { height: 5, backgroundColor: C.mutedBg, borderRadius: 999, overflow: 'hidden', flex: 1 },
  biasFill: { height: '100%', borderRadius: 999 },
  biasScore: { fontSize: 12, fontWeight: '500', width: 24, textAlign: 'right' },
  topBiasCard: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start' },
  topBiasLabel: { fontSize: 13, color: '#94a3b8', lineHeight: 18, flex: 1, paddingRight: 10 },
  topBiasTag: { fontSize: 17, fontWeight: '600', color: '#16213b', lineHeight: 18 },
  topBiasCount: { fontSize: 12, color: '#94a3b8', marginTop: 4 },
  compareSubtitle: { fontSize: 13, color: '#94a3b8' },
  legendRow: { flexDirection: 'row', gap: 16, marginTop: 8 },
  legendItem: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  legendDot: { width: 9, height: 9, borderRadius: 5 },
  legendText: { fontSize: 12, color: C.navy },
  insightBlock: { flexDirection: 'row', gap: 10, backgroundColor: '#eff6ff', borderRadius: 18, padding: 13, marginTop: 16, alignItems: 'flex-start' },
  insightIconBox: { width: 19, height: 19, borderRadius: 10, backgroundColor: C.blue, alignItems: 'center', justifyContent: 'center', marginTop: 1 },
  insightIconText: { color: '#fff', fontSize: 15, fontWeight: '700' },
  insightText: { flex: 1, fontSize: 14, color: C.navy, lineHeight: 19 },
  insightNum: { color: C.blue, fontWeight: '600' },
  trendGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 13 },
  trendCard: { width: '46%', flexGrow: 1, borderRadius: 26, padding: 10, paddingTop: 14 },
  trendHeader: { flexDirection: 'row', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: 8, paddingHorizontal: 4 },
  trendLabel: { fontSize: 13, fontWeight: '500', color: C.navy },
  trendValue: { fontSize: 17, fontWeight: '600' },
  trendUnit: { fontSize: 12, fontWeight: '400', color: C.muted },
});
