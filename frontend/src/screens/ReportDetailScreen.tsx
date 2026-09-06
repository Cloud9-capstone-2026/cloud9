import React, { useMemo, useState } from 'react';
import { View, Text, Pressable, ScrollView, NativeSyntheticEvent, NativeScrollEvent, StyleSheet } from 'react-native';
import { useRoute, RouteProp } from '@react-navigation/native';
import { Screen } from '../components/Screen';
import { Card } from '../components/Card';
import { NewsRow } from '../components/NewsRow';
import { LayerRing } from '../components/charts/LayerRing';
import { C, DEVIATION_GAUGE, shadow } from '../theme/tokens';
import { dartNews } from '../data/mock';
import { buildReportDetailVM } from './reportDetailLogic';
import type { RootStackParamList } from '../navigation/types';

const SEG_LABELS = ['~1σ', '~2σ', '~3σ', '3σ+'];

export function ReportDetailScreen() {
  const route = useRoute<RouteProp<RootStackParamList, 'ReportDetail'>>();
  const { tradeId } = route.params;
  const d = useMemo(() => buildReportDetailVM(tradeId), [tradeId]);
  const [evOpen, setEvOpen] = useState<Record<string, boolean>>({});
  const [ruleScroll, setRuleScroll] = useState({ pos: 0, trackH: 0, contentH: 0 });

  const onRuleScroll = (e: NativeSyntheticEvent<NativeScrollEvent>) => {
    const { contentOffset, contentSize, layoutMeasurement } = e.nativeEvent;
    const maxScroll = Math.max(1, contentSize.height - layoutMeasurement.height);
    setRuleScroll({ pos: contentOffset.y / maxScroll, trackH: layoutMeasurement.height, contentH: contentSize.height });
  };
  const ruleCount = d.rules.length;
  const showRuleScrollbar = ruleCount > 4;
  const thumbRatio = Math.max(0.28, 4 / Math.max(ruleCount, 1));
  const thumbH = ruleScroll.trackH * thumbRatio;
  const thumbTop = (ruleScroll.trackH - thumbH) * ruleScroll.pos;
  const relatedNews = useMemo(() => dartNews.slice(0, 3), []);

  return (
    <Screen back contentStyle={styles.content}>
      <View style={styles.headerRow}>
        <Text style={styles.stockName}>{d.stock}</Text>
        <Text style={styles.dateText}>분석일자 2026.07.31</Text>
      </View>

      <View>
        <Text style={styles.sectionTitle}>거래 상세</Text>
        <Card>
          <View style={styles.detailGrid}>
            {d.rows.map((r) => (
              <View key={r.k} style={styles.detailCell}>
                <Text style={styles.detailLabel}>{r.k}</Text>
                <Text style={styles.detailValue}>{r.v}</Text>
              </View>
            ))}
          </View>
        </Card>
      </View>

      <View>
        <Text style={styles.sectionTitle}>분석 결과</Text>
        <View style={{ gap: 13 }}>
          <Card style={styles.resultCard}>
            <View style={{ marginBottom: 14 }}>
              <Text style={styles.layerSummary}>{d.layerSummary}</Text>
              <Text style={[styles.verdict, { color: d.verdictColor }]}>{d.verdict}</Text>
            </View>
            <View style={styles.layersRow}>
              {d.layers.map((l) => (
                <View key={l.label} style={styles.layerItem}>
                  <LayerRing score={l.score} triggered={l.triggered} failed={l.failed} />
                  <Text style={{ fontSize: 13, color: l.triggered ? C.navy : C.muted, fontWeight: l.triggered ? '600' : '400' }}>
                    {l.label}
                  </Text>
                </View>
              ))}
            </View>
            {d.lstmFailed && (
              <View style={styles.lstmFailNote}>
                <Text style={{ fontSize: 11, color: C.muted }}>딥러닝 계층 분석 실패</Text>
              </View>
            )}
          </Card>

          <View style={styles.twoColRow}>
            <Card style={[styles.twoColCard, styles.rulesCard]}>
              <Text style={styles.smallCardTitle}>위반한 규칙</Text>
              <View style={styles.rulesBody}>
                <ScrollView
                  style={{ flex: 1 }}
                  contentContainerStyle={{ paddingRight: showRuleScrollbar ? 12 : 0, gap: 4 }}
                  showsVerticalScrollIndicator={false}
                  onScroll={onRuleScroll}
                  scrollEventThrottle={16}
                  onLayout={(e) => setRuleScroll((s) => ({ ...s, trackH: e.nativeEvent.layout.height }))}
                >
                  {d.rules.map((r) => (
                    <Text key={r} style={styles.ruleText}>{r}</Text>
                  ))}
                </ScrollView>
                {showRuleScrollbar && (
                  <View style={styles.rulesTrack}>
                    <View style={[styles.rulesThumb, { height: thumbH, top: thumbTop }]} />
                  </View>
                )}
              </View>
            </Card>
            <Card style={[styles.twoColCard, styles.deviationCard]}>
              <View>
                <Text style={styles.smallCardTitle}>평소 패턴 대비 이탈도</Text>
                <Text style={styles.devLabel}>{d.devLabel}</Text>
                <Text style={styles.sigmaText}>{d.sigmaText}</Text>
              </View>
              <View>
                <View style={styles.gaugeTrack}>
                  {DEVIATION_GAUGE.map((c, i) => (
                    <View key={i} style={[styles.gaugeSeg, { backgroundColor: c }]} />
                  ))}
                  <View style={[styles.gaugeMarker, { left: `${d.markerPct}%`, backgroundColor: d.markerColor }]} />
                </View>
                <View style={styles.gaugeLabelRow}>
                  {SEG_LABELS.map((label, i) => (
                    <Text
                      key={label}
                      style={[styles.gaugeLabel, { color: i === d.activeSeg ? '#111' : C.muted, fontWeight: i === d.activeSeg ? '600' : '400' }]}
                    >
                      {label}
                    </Text>
                  ))}
                </View>
              </View>
            </Card>
          </View>
        </View>
      </View>

      {d.showBias && (
        <View>
          <Text style={styles.sectionTitle}>편향 분석</Text>
          <Card>
            <View style={{ gap: 11 }}>
              {d.biasRows.map((b) => (
                <View key={b.key}>
                  <View style={styles.biasHeaderRow}>
                    <View style={styles.biasHeaderLeft}>
                      <Text style={{ fontSize: 15, fontWeight: b.isTop ? '600' : '400', color: b.isTop ? C.navy : C.muted }}>
                        {b.name}
                      </Text>
                      {b.isTop && (
                        <View style={styles.topBadge}>
                          <Text style={styles.topBadgeText}>주요 의심</Text>
                        </View>
                      )}
                    </View>
                    <Text style={{ fontSize: 15, fontWeight: '600', color: b.color }}>{b.score}</Text>
                  </View>
                  <View style={styles.biasTrack}>
                    <View style={[styles.biasFill, { width: `${b.score}%`, backgroundColor: b.color }]} />
                  </View>
                </View>
              ))}
            </View>
          </Card>
        </View>
      )}

      {d.showEvidence && (
        <View>
          <Text style={styles.sectionTitle}>판정 근거</Text>
          <Card>
            <Text style={styles.evidenceDesc}>
              AI 모델의 내부 분석 결과를 바탕으로, 각 편향에 영향을 준 요인의 순위와 방향(편향 강화 / 약화)을 보여줘요.
            </Text>
            <View style={{ gap: 18 }}>
              {d.evidence.map((e) => {
                const open = !!evOpen[e.key];
                return (
                  <View key={e.key}>
                    <View style={styles.evNameRow}>
                      <View style={[styles.evDot, { backgroundColor: e.color }]} />
                      <Text style={{ fontSize: 15, color: C.navy, fontWeight: e.isTop ? '600' : '500' }}>{e.name}</Text>
                    </View>
                    <View style={{ marginBottom: 9 }}>
                      <View style={styles.evShareLabelRow}>
                        <Text style={styles.evShareLabel}>이번 거래 영향</Text>
                        <Text style={styles.evShareLabel}>과거 패턴 영향</Text>
                      </View>
                      <View style={styles.evShareTrack}>
                        <View style={[styles.evShareFill, { width: `${e.tradePct}%`, backgroundColor: e.color }]} />
                        <View style={styles.evShareRest} />
                      </View>
                      <View style={styles.evShareLabelRow}>
                        <Text style={[styles.evShareValue, { color: e.color }]}>{e.tradeLabel}</Text>
                        <Text style={[styles.evShareValue, { color: '#64748B' }]}>{e.contextLabel}</Text>
                      </View>
                    </View>
                    <Pressable
                      onPress={() => setEvOpen((prev) => ({ ...prev, [e.key]: !prev[e.key] }))}
                      style={styles.evToggle}
                    >
                      <Text style={{ fontSize: 13, color: C.navy }}>영향을 준 요인 보기</Text>
                      <Text style={styles.evCaret}>{open ? '▲' : '▼'}</Text>
                    </Pressable>
                    {open && (
                      <View style={styles.evList}>
                        {e.ranked.map((f, i) => (
                          <View key={f.name} style={[styles.evListRow, i > 0 && styles.evListDivider]}>
                            <Text style={styles.evRank}>{f.rank}</Text>
                            <Text style={styles.evFeatureName}>{f.name}</Text>
                            <Text style={[styles.evDir, { color: f.dirColor }]}>{f.dir}</Text>
                          </View>
                        ))}
                      </View>
                    )}
                  </View>
                );
              })}
            </View>
          </Card>
        </View>
      )}

      <View>
        <View style={styles.newsHeaderRow}>
          <Text style={styles.sectionTitle}>관련 공시·뉴스</Text>
          <View style={styles.dartBadge}>
            <Text style={styles.dartBadgeText}>DART</Text>
          </View>
        </View>
        <Text style={styles.newsCaution}>※ 아래 공시·뉴스는 분석 근거가 아닌 참고용 정보입니다.</Text>
        {relatedNews.length > 0 ? (
          <Card>
            {relatedNews.map((n, i) => (
              <NewsRow key={n.id} news={n} index={i} showCorp={false} />
            ))}
          </Card>
        ) : (
          <Card style={styles.newsEmptyCard}>
            <Text style={styles.newsEmptyText}>관련 공시·뉴스가 없어요</Text>
          </Card>
        )}
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  content: { gap: 22 },
  headerRow: { flexDirection: 'row', alignItems: 'baseline', justifyContent: 'space-between', paddingBottom: 2 },
  stockName: { fontSize: 27, fontWeight: '700', color: C.navy, letterSpacing: -0.5 },
  dateText: { fontSize: 13, color: C.muted },
  sectionTitle: { fontSize: 20, fontWeight: '600', color: C.navy, letterSpacing: -0.1, paddingHorizontal: 2, marginBottom: 10 },
  detailGrid: { flexDirection: 'row', flexWrap: 'wrap', rowGap: 19 },
  detailCell: { width: '50%' },
  detailLabel: { fontSize: 12, color: C.muted, marginBottom: 3 },
  detailValue: { fontSize: 16, fontWeight: '500', color: C.navy },
  resultCard: { paddingVertical: 18 },
  layerSummary: { fontSize: 13, color: C.muted, marginBottom: 4 },
  verdict: { fontSize: 25, fontWeight: '600', letterSpacing: -0.5 },
  layersRow: { flexDirection: 'row', justifyContent: 'space-around' },
  layerItem: { alignItems: 'center', gap: 6 },
  lstmFailNote: { marginTop: 12, paddingVertical: 7, paddingHorizontal: 11, backgroundColor: C.mutedBg, borderRadius: 10 },
  twoColRow: { flexDirection: 'row', gap: 13 },
  twoColCard: { flex: 1, minHeight: 160, padding: 14 },
  rulesCard: { height: 160, minHeight: undefined },
  rulesBody: { flex: 1, flexDirection: 'row' },
  rulesTrack: { width: 5, borderRadius: 3, backgroundColor: '#eef2f7', marginLeft: 4 },
  rulesThumb: { position: 'absolute', width: 5, borderRadius: 3, backgroundColor: '#cbd5e1' },
  smallCardTitle: { fontSize: 13, fontWeight: '500', color: C.muted, marginBottom: 7 },
  ruleText: { fontSize: 16, fontWeight: '700', color: '#111', lineHeight: 21.7 },
  deviationCard: { justifyContent: 'space-between' },
  devLabel: { fontSize: 17, fontWeight: '700', color: '#111', lineHeight: 20, marginBottom: 4 },
  sigmaText: { fontSize: 15, fontWeight: '500', color: C.muted },
  gaugeTrack: { flexDirection: 'row', gap: 3, height: 7, borderRadius: 999, overflow: 'visible' },
  gaugeSeg: { flex: 1, borderRadius: 999 },
  gaugeMarker: {
    position: 'absolute', top: '50%', marginTop: -6, marginLeft: -6,
    width: 12, height: 12, borderRadius: 6, borderWidth: 2, borderColor: '#fff',
    ...shadow.marker,
  },
  gaugeLabelRow: { flexDirection: 'row', marginTop: 6 },
  gaugeLabel: { flex: 1, textAlign: 'center', fontSize: 10 },
  biasHeaderRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 5 },
  biasHeaderLeft: { flexDirection: 'row', alignItems: 'center', gap: 7 },
  topBadge: { backgroundColor: '#e8f0ff', borderRadius: 999, paddingVertical: 2, paddingHorizontal: 8 },
  topBadgeText: { fontSize: 11, fontWeight: '500', color: C.blue },
  biasTrack: { height: 5, backgroundColor: C.mutedBg, borderRadius: 999, overflow: 'hidden' },
  biasFill: { height: '100%', borderRadius: 999 },
  evidenceDesc: { fontSize: 13, color: C.muted, lineHeight: 19, marginBottom: 14 },
  evNameRow: { flexDirection: 'row', alignItems: 'center', gap: 7, marginBottom: 9 },
  evDot: { width: 8, height: 8, borderRadius: 2 },
  evShareLabelRow: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 4, marginTop: 3 },
  evShareLabel: { fontSize: 11, color: C.muted },
  evShareTrack: { height: 6, backgroundColor: C.mutedBg, borderRadius: 999, overflow: 'hidden', flexDirection: 'row' },
  evShareFill: { borderRadius: 999 },
  evShareRest: { flex: 1, backgroundColor: '#CBD5E1' },
  evShareValue: { fontSize: 11, fontWeight: '500' },
  evToggle: {
    width: '100%', backgroundColor: C.mutedBg, borderRadius: 12, paddingVertical: 9, paddingHorizontal: 12,
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
  },
  evCaret: { color: C.muted, fontSize: 11, fontWeight: '600' },
  evList: { marginTop: 8, backgroundColor: C.subtleBg, borderRadius: 14, paddingHorizontal: 12 },
  evListRow: { flexDirection: 'row', alignItems: 'center', gap: 9, paddingVertical: 9 },
  evListDivider: { borderTopWidth: 1, borderTopColor: C.border },
  evRank: { fontSize: 12, fontWeight: '600', color: C.muted, width: 14, textAlign: 'right' },
  evFeatureName: { fontSize: 13, color: C.navy, flex: 1 },
  evDir: { fontSize: 12, fontWeight: '600' },
  newsHeaderRow: { flexDirection: 'row', alignItems: 'center', gap: 7, paddingHorizontal: 2, marginBottom: 0 },
  dartBadge: { backgroundColor: C.mutedBg, borderRadius: 999, paddingVertical: 2, paddingHorizontal: 8 },
  dartBadgeText: { fontSize: 11, color: C.muted },
  newsCaution: { fontSize: 12, color: C.muted, marginBottom: 10, marginTop: 2, paddingHorizontal: 2, lineHeight: 18 },
  newsEmptyCard: { height: 118, alignItems: 'center', justifyContent: 'center' },
  newsEmptyText: { fontSize: 15, color: C.muted },
});
