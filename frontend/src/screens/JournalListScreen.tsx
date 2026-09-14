import React, { useCallback, useMemo, useState } from 'react';
import { View, Text, Pressable, StyleSheet } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { Screen } from '../components/Screen';
import { Card, CARD_PADDING } from '../components/Card';
import { GradientCard } from '../components/GradientCard';
import { EmptyState } from '../components/EmptyState';
import { JournalRow, JOURNAL_ROW_HEIGHT } from '../components/JournalRow';
import { RadarChart } from '../components/charts/RadarChart';
import { C, ACCENT, EMOTIONS, shadow, text } from '../theme/tokens';
import type { TradeRaw } from '../api/trades';
import type { AnalysisResult } from '../api/analysis';
import { formatDate } from '../utils/formatDate';
import { buildAnalysisLookup, findAnalysisForTrade, verdictToRisk } from '../utils/matchTradeAnalysis';
import { useAppState } from '../state/AppState';
import { goToJournalFullList, goToJournalPending, goToJournalWrite } from '../navigation/navigationRef';

const RECENT_JOURNALS_VISIBLE = 5;

export function JournalListScreen() {
  const { journals, refreshJournals, isJournaled, getAllTrades, getAllAnalysis } = useAppState();
  const [trades, setTrades] = useState<TradeRaw[]>([]);
  const [analysis, setAnalysis] = useState<AnalysisResult[]>([]);

  useFocusEffect(
    useCallback(() => {
      let cancelled = false;
      (async () => {
        try {
          const [tradesRes, analysisRes] = await Promise.all([getAllTrades(), getAllAnalysis()]);
          if (!cancelled) {
            setTrades(tradesRes);
            setAnalysis(analysisRes);
          }
        } catch {
          // 네트워크 실패 — 이전 값 유지
        }
      })();
      // 일지 목록은 별도 상태(AppState)라 실패해도 위 거래/분석 표시를 막으면 안 되므로 독립적으로 불러온다.
      refreshJournals().catch(() => {});
      return () => { cancelled = true; };
    }, [getAllTrades, getAllAnalysis, refreshJournals])
  );

  const hasUploaded = trades.length > 0;
  const hasJournals = journals.length > 0;
  // 전체 거래일지 중 각 감정 태그가 차지하는 비율(%) — 레이더 차트 축 10개는 항상
  // EMOTIONS 순서 고정, 값은 0~100 사이의 백분율(태그 건수 / 전체 일지 건수 * 100).
  const emotionPercents = useMemo(() => {
    const total = journals.length;
    if (total === 0) return EMOTIONS.map(() => 0);
    return EMOTIONS.map((e) => {
      const count = journals.filter((j) => j.emotion === e).length;
      return Math.round((count / total) * 1000) / 10;
    });
  }, [journals]);
  const analysisLookup = useMemo(() => buildAnalysisLookup(analysis), [analysis]);
  const tradeById = useMemo(() => new Map(trades.map((t) => [t.id, t])), [trades]);

  // 일지를 쓸 수 있는 대상 = 분석 결과가 있는(=정상적으로 분석까지 끝난) 거래만 —
  // JournalPendingScreen의 정의와 동일하게 맞춰서 이 배너 숫자와 실제 목록 건수가 일치하게 한다.
  const pendingCount = useMemo(
    () => trades.filter((t) => findAnalysisForTrade(analysisLookup, t) !== null && !isJournaled(t.id)).length,
    [trades, analysisLookup, isJournaled]
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

  const recentJournals = useMemo(
    () => journals.slice(0, RECENT_JOURNALS_VISIBLE).map((j) => {
      const t = tradeById.get(j.trade_id);
      const match = t ? findAnalysisForTrade(analysisLookup, t) : null;
      return { journal: j, risk: match ? verdictToRisk(match.detail.verdict) : null };
    }),
    [journals, tradeById, analysisLookup]
  );

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
              axes={EMOTIONS}
              series={hasJournals ? [{ values: emotionPercents, color: ACCENT, fillOpacity: 0.28, width: 1.5 }] : []}
              size={165}
              radius={50}
              max={100}
              fontSize={8}
              height={160}
              dots={hasJournals}
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
        <Card style={hasUploaded ? styles.recentCardFilled : styles.recentCardEmpty}>
          {hasUploaded ? (
            recentJournals.map(({ journal: j, risk: r }, i) => (
              <JournalRow
                key={j.id}
                journal={{ ...j, date: formatDate(j.date) }}
                risk={r}
                index={i}
                onPress={() => goToJournalWrite(j.id)}
              />
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
  recentCardFilled: { minHeight: JOURNAL_ROW_HEIGHT * RECENT_JOURNALS_VISIBLE + CARD_PADDING * 2 },
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
