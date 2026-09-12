import React, { useCallback, useMemo, useState } from 'react';
import { View, Text, Image, Pressable, StyleSheet } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { Screen } from '../components/Screen';
import { Card, CARD_PADDING } from '../components/Card';
import { EmptyState } from '../components/EmptyState';
import { TradeRow, TRADE_ROW_HEIGHT } from '../components/TradeRow';
import { NewsRow } from '../components/NewsRow';
import { RingChart } from '../components/charts/RingChart';
import { MonthlyBarChart, MONTHLY_CHART_HEIGHT } from '../components/charts/MonthlyBarChart';
import { AnomalyTrendChart } from '../components/charts/AnomalyTrendChart';
import { Avatar } from '../assets/Avatar';
import { C, RISK, BIAS_LABELS, BIAS_COLORS, BIAS_KEYS, text } from '../theme/tokens';
import { dartNews } from '../data/mock';
import type { Trade } from '../data/types';
import type { SurveyResult } from '../api/survey';
import type { AnalysisResult } from '../api/analysis';
import type { TradeRaw, UploadHistoryItem } from '../api/trades';
import { getCharacter } from '../constants/characterAssets';
import { formatDate } from '../utils/formatDate';
import { buildMonthlyWindow } from '../utils/buildMonthlyWindow';
import { buildAnalysisLookup, findAnalysisForTrade, verdictToRisk } from '../utils/matchTradeAnalysis';
import { goToTab, goToNewsFullList, goToReportDetail } from '../navigation/navigationRef';
import { useAppState } from '../state/AppState';

const RECENT_TRADES_VISIBLE = 5;

function toTradeShape(t: TradeRaw): Trade {
  return {
    id: t.id,
    stock: t.종목명,
    date: formatDate(t.거래일자),
    type: t.거래구분 === '매도' ? 'sell' : 'buy',
    price: t.거래단가.toLocaleString(),
    qty: t.거래수량,
    amount: t.거래금액.toLocaleString(),
    score: 0,
    deviation: 0,
  };
}

export function HomeScreen() {
  const { openBiasInfo, pfName, getLatestSurvey, getAllTrades, getAllAnalysis, getUploads } = useAppState();
  const [chartTab, setChartTab] = useState<'trades' | 'anomaly'>('trades');
  const [latest, setLatest] = useState<SurveyResult | null | undefined>(undefined);
  const [trades, setTrades] = useState<TradeRaw[]>([]);
  const [analysis, setAnalysis] = useState<AnalysisResult[]>([]);
  const [uploads, setUploads] = useState<UploadHistoryItem[]>([]);

  useFocusEffect(
    useCallback(() => {
      let cancelled = false;
      (async () => {
        try {
          const [latestRes, tradesRes, analysisRes, uploadsRes] = await Promise.all([
            getLatestSurvey(), getAllTrades(), getAllAnalysis(), getUploads(1, 0),
          ]);
          if (!cancelled) {
            setLatest(latestRes);
            setTrades(tradesRes);
            setAnalysis(analysisRes);
            setUploads(uploadsRes);
          }
        } catch {
          // 네트워크 실패 시 기존 값 유지
        }
      })();
      return () => { cancelled = true; };
    }, [getLatestSurvey, getAllTrades, getAllAnalysis, getUploads])
  );

  const character = latest ? getCharacter(latest.type_code) : null;
  const hasData = trades.length > 0;

  const counts = useMemo(() => {
    let danger = 0, caution = 0, safe = 0;
    analysis.forEach((a) => {
      const r = verdictToRisk(a.detail.verdict);
      if (r === 'danger') danger++;
      else if (r === 'caution') caution++;
      else safe++;
    });
    return { danger, caution, safe };
  }, [analysis]);

  const anomalyRate = analysis.length > 0
    ? Math.round((analysis.filter((a) => a.is_anomaly).length / analysis.length) * 1000) / 10
    : 0;

  // 가장 최근 업로드가 반영되기 전(그 업로드분을 뺀) 상태와 지금(전체)을 비교한 증감.
  // 첫 업로드라 "이전" 자체가 없으면(beforeAnalysis 0건) 증감이 곧 현재값 전체가 된다.
  const latestUploadId = uploads[0]?.id;
  const diff = useMemo(() => {
    if (latestUploadId == null) return null;
    const beforeTrades = trades.filter((t) => t.upload_id !== latestUploadId).length;
    const tradesDiff = trades.length - beforeTrades;

    const beforeAnalysis = analysis.filter((a) => a.upload_id !== latestUploadId);
    const beforeRate = beforeAnalysis.length > 0
      ? Math.round((beforeAnalysis.filter((a) => a.is_anomaly).length / beforeAnalysis.length) * 1000) / 10
      : 0;
    const rateDiff = Math.round((anomalyRate - beforeRate) * 10) / 10;

    return { tradesDiff, rateDiff };
  }, [trades, analysis, latestUploadId, anomalyRate]);

  const monthly = useMemo(
    () => buildMonthlyWindow(
      trades.map((t) => t.거래일자),
      analysis.filter((a) => a.is_anomaly).map((a) => a.detail.날짜)
    ),
    [trades, analysis]
  );

  const analysisLookup = useMemo(() => buildAnalysisLookup(analysis), [analysis]);
  const recentTrades = trades.slice(0, RECENT_TRADES_VISIBLE);
  const lastUploadDate = uploads[0]?.uploaded_at ? formatDate(uploads[0].uploaded_at) : null;

  return (
    <Screen contentStyle={styles.content}>
      <View>
        <Text style={text.screenTitle}>안녕하세요, {pfName}님</Text>
        <Text style={[text.screenSubtitle, styles.lastUpload]}>
          {lastUploadDate ? `마지막 업로드 ${lastUploadDate}` : '아직 업로드한 거래 내역이 없어요'}
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
                  { label: '이상', color: RISK.danger.ring, text: hasData ? `${counts.danger}건` : '-건' },
                  { label: '경고', color: RISK.caution.ring, text: hasData ? `${counts.caution}건` : '-건' },
                  { label: '정상', color: RISK.safe.ring, text: hasData ? `${counts.safe}건` : '-건' },
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
                <Text style={styles.summaryValue}>{hasData ? trades.length : '-'}</Text>
                <Text style={styles.summaryUnit}>건</Text>
              </View>
              <Text style={[styles.summaryDiff, { color: hasData ? C.red : C.muted }]}>
                {hasData && diff ? `${diff.tradesDiff >= 0 ? '+' : '-'} ${Math.abs(diff.tradesDiff)}건` : '- 건'}
              </Text>
            </Card>
            <Card style={styles.summaryCard}>
              <Text style={styles.summaryLabel}>이상 탐지율</Text>
              <View style={styles.summaryValueRow}>
                <Text style={styles.summaryValue}>{hasData ? anomalyRate : '-'}</Text>
                <Text style={styles.summaryUnit}>%</Text>
              </View>
              <Text style={[styles.summaryDiff, { color: hasData ? C.blue : C.muted }]}>
                {hasData && diff ? `${diff.rateDiff >= 0 ? '+' : '-'} ${Math.abs(diff.rateDiff)}%` : '- %'}
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
        <Card style={[styles.chartCard, !hasData && styles.chartCardEmpty]}>
          {!hasData ? (
            <EmptyState title="아직 업로드한 거래 내역이 없어요" />
          ) : chartTab === 'trades' ? (
            <MonthlyBarChart months={monthly.months} values={monthly.tradeCounts} />
          ) : (
            <AnomalyTrendChart months={monthly.months} values={monthly.anomalyCounts} />
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
        <Card style={!hasData && styles.recentTradesCardEmpty}>
          {hasData ? (
            recentTrades.map((t, i) => {
              const match = findAnalysisForTrade(analysisLookup, t);
              return (
                <TradeRow
                  key={t.id}
                  trade={toTradeShape(t)}
                  index={i}
                  risk={match ? verdictToRisk(match.detail.verdict) : 'safe'}
                  onPress={() => goToReportDetail(t.id)}
                />
              );
            })
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
