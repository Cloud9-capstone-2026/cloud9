import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { Card } from './Card';
import { C, BIAS_KEYS, BIAS_LABELS, BIAS_COLORS } from '../theme/tokens';
import { hasBatchim, withTopicParticle } from '../utils/korean';
import type { BiasShareResult } from '../utils/buildBiasShare';
import type { BiasKey } from '../theme/tokens';

const HEADLINE: Record<Exclude<BiasShareResult['status'], 'ok'>, string> = {
  loading: '불러오는 중이에요',
  noSurvey: '자가진단을 먼저 해보세요',
  noTrades: '거래 내역을 올리면\n비교할 수 있어요',
  noSelfScore: '아직 비교할 수 없어요',
  noDetection: '아직 감지된 편향이\n없어요',
};

// 아래 막대 우측의 보조 라벨 — 상태마다 분모가 달라서 문구도 달라진다.
const DETECT_SUB: Record<Exclude<BiasShareResult['status'], 'ok'>, string> = {
  loading: '',
  noSurvey: '',
  noTrades: '분석된 거래 없음',
  noSelfScore: '',
  noDetection: '감지된 편향 없음',
};

const labelOf = (key: BiasKey) => BIAS_LABELS[BIAS_KEYS.indexOf(key)];
const colorOf = (key: BiasKey) => BIAS_COLORS[BIAS_KEYS.indexOf(key)];

function ShareBar({ values, keys }: { values: (key: BiasKey) => number | null; keys: BiasKey[] }) {
  const segments = keys
    .map((key) => ({ key, value: values(key) }))
    .filter((s): s is { key: BiasKey; value: number } => s.value != null && s.value > 0);
  if (segments.length === 0) {
    return (
      <View style={[styles.bar, styles.barEmpty]}>
        <Text style={styles.barEmptyText}>비교할 수 없어요</Text>
      </View>
    );
  }
  return (
    <View style={styles.bar}>
      {segments.map(({ key, value }) => (
        <View key={key} style={[styles.seg, { width: `${value}%`, backgroundColor: colorOf(key) }]}>
          {/* 폭이 좁으면 숫자가 잘려 보여서 일정 비중 이상일 때만 표시 */}
          {value >= 11 && <Text style={styles.segText}>{value}%</Text>}
        </View>
      ))}
    </View>
  );
}

export function BiasShareCompare({ data }: { data: BiasShareResult }) {
  const { status, keys, rows, detectedCount, headlineKey, headlineBigger, excludedKeys } = data;

  const headline = status !== 'ok' ? HEADLINE[status] : '생각과 실제가\n대체로 비슷해요';

  // 변화가 큰 순으로 — 어긋난 것부터 읽히게. 제외된 축은 비교값이 없어 맨 뒤로.
  const sortedRows = [...rows].sort((a, b) => {
    if (a.excluded !== b.excluded) return a.excluded ? 1 : -1;
    return Math.abs(b.diff ?? -1) - Math.abs(a.diff ?? -1);
  });

  return (
    <Card>
      <Text style={styles.eyebrow}>검사 결과 vs 실제 거래</Text>
      <Text style={styles.headline}>
        {status === 'ok' && headlineKey ? (
          <>
            <Text style={{ color: headlineBigger ? C.red : C.blue }}>{labelOf(headlineKey)}</Text>
            {`${hasBatchim(labelOf(headlineKey)) ? '이' : '가'} 생각보다\n${headlineBigger ? '크게' : '작게'} 나타나요`}
          </>
        ) : headline}
      </Text>

      <View style={styles.block}>
        <View style={styles.blockTop}>
          <Text style={styles.blockLabel}>내가 생각한 나</Text>
          <Text style={styles.blockSub}>자가진단 결과</Text>
        </View>
        <ShareBar keys={keys} values={(key) => rows.find((r) => r.key === key)?.self ?? null} />
      </View>

      <View style={styles.block}>
        <View style={styles.blockTop}>
          <Text style={styles.blockLabel}>실제 데이터로 본 나</Text>
          <Text style={styles.blockSub}>
            {status === 'ok' ? `편향이 감지된 ${detectedCount}건` : DETECT_SUB[status]}
          </Text>
        </View>
        <ShareBar keys={keys} values={(key) => rows.find((r) => r.key === key)?.trading ?? null} />
        <Text style={styles.subnote}>
          편향마다 판단 대상 거래가 달라 매수·매도 비중에 따라 비율이 달라질 수 있습니다.
        </Text>
      </View>

      <View style={styles.list}>
        {sortedRows.map((row) => (
          <View key={row.key} style={styles.listRow}>
            <View style={[styles.listDot, { backgroundColor: colorOf(row.key) }]} />
            <Text style={styles.listName}>{labelOf(row.key)}</Text>
            <Text style={styles.listValue}>
              {row.self != null ? `${row.self}%` : '—'} → {row.trading != null ? `${row.trading}%` : '—'}
            </Text>
            <Text
              style={[
                styles.listDiff,
                { color: row.diff == null ? C.muted : row.diff > 0 ? C.red : row.diff < 0 ? C.blue : C.muted },
              ]}
            >
              {row.diff == null ? '비교 불가' : row.diff === 0 ? '–' : `${row.diff > 0 ? '▲' : '▼'}${Math.abs(row.diff)}`}
            </Text>
          </View>
        ))}
      </View>

      {excludedKeys.length > 0 && (
        <Text style={styles.note}>
          {withTopicParticle(excludedKeys.map(labelOf).join('·'))} 해당 거래가 아직 없어 비교에서 제외했습니다.
        </Text>
      )}
    </Card>
  );
}

const styles = StyleSheet.create({
  eyebrow: { fontSize: 13, color: C.muted, marginBottom: 4 },
  headline: { fontSize: 18, fontWeight: '700', color: C.navy, letterSpacing: -0.3, lineHeight: 26, marginBottom: 18 },
  block: { marginBottom: 14 },
  blockTop: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 13 },
  blockLabel: { fontSize: 13, fontWeight: '600', color: C.navy },
  blockSub: { fontSize: 11, color: C.muted },
  bar: { flexDirection: 'row', height: 30, borderRadius: 9, overflow: 'hidden', backgroundColor: C.mutedBg },
  barEmpty: { alignItems: 'center', justifyContent: 'center' },
  barEmptyText: { fontSize: 12, fontWeight: '600', color: C.muted },
  seg: { alignItems: 'center', justifyContent: 'center' },
  segText: { fontSize: 11, fontWeight: '600', color: '#fff' },
  subnote: { fontSize: 10, color: C.muted, lineHeight: 15, marginTop: 9, textAlign: 'center' },
  list: { marginTop: 6, paddingTop: 13, borderTopWidth: 1, borderTopColor: C.border, gap: 9 },
  listRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  listDot: { width: 9, height: 9, borderRadius: 3 },
  listName: { fontSize: 12, fontWeight: '600', color: C.navy, flex: 1 },
  listValue: { fontSize: 11.5, color: C.muted },
  listDiff: { fontSize: 11.5, fontWeight: '700', minWidth: 48, textAlign: 'right' },
  note: { fontSize: 11, color: C.muted, lineHeight: 16, backgroundColor: C.mutedBg, borderRadius: 10, paddingVertical: 9, paddingHorizontal: 11, marginTop: 14 },
});
