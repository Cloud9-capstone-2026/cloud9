import React, { useEffect, useState } from 'react';
import { View, Text, Pressable, StyleSheet } from 'react-native';
import { GradientCard } from './GradientCard';
import { CARD_PADDING } from './Card';
import { IconLightbulb, IconSearch } from '../assets/icons';
import { C, ACCENT, BIAS_KEY_MAP } from '../theme/tokens';
import { useAppState } from '../state/AppState';
import { goToRulesSettings } from '../navigation/navigationRef';
import type { RuleAdviceItem } from '../api/analysis';
import type { RuleEffectResponse } from '../api/rules';

const ADVICE_TITLE: Record<string, string> = {
  daily_total_cap: '매매대금 상한을 켜보세요',
  min_holding: '최소 보유기간을 켜보세요',
};

// 위반 = "이 금액을 넘었다"(금액 상한) / "기준보다 일찍 팔았다"(보유기간) — 규칙마다 다른 의미라
// 미리보기 문장도 규칙별로 갈라서 쓴다.
const VIOLATION_PHRASE: Record<string, string> = {
  daily_total_cap: '이 금액을 넘었을',
  min_holding: '기준보다 일찍 팔았을',
};
const NO_VIOLATION_PHRASE: Record<string, string> = {
  daily_total_cap: '이 금액을 넘은 적은',
  min_holding: '기준보다 일찍 판 적은',
};

function AdviceBody({ advice }: { advice: RuleAdviceItem }) {
  const biasLabel = BIAS_KEY_MAP[advice.bias];
  if (advice.rule_id === 'daily_total_cap') {
    const amount = `${Math.round(advice.suggested_param / 10000).toLocaleString()}만원`;
    return (
      <Text style={styles.body}>
        최근 거래가 <Text style={styles.bodyBold}>{biasLabel}</Text> 패턴에 가까워요.{'\n'}
        하루 매매대금을 <Text style={styles.bodyBold}>{amount}</Text>으로 제한해볼까요?
      </Text>
    );
  }
  if (advice.rule_id === 'min_holding') {
    const days = `${advice.suggested_param}${advice.param_unit ?? '일'}`;
    return (
      <Text style={styles.body}>
        최근 거래가 <Text style={styles.bodyBold}>{biasLabel}</Text> 패턴에 가까워요.{'\n'}
        최소 보유기간을 <Text style={styles.bodyBold}>{days}</Text>로 정해볼까요?
      </Text>
    );
  }
  return null;
}

// 거래 1건의 규칙 조언(서버 detail.rule_advice[i]) → 카드 하나. "편향 분석"과 "판정 근거" 사이에 둔다.
export function RuleAdviceCard({ advice, disclaimer }: { advice: RuleAdviceItem; disclaimer: string | null }) {
  const { getRuleEffect } = useAppState();
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading');
  const [effect, setEffect] = useState<RuleEffectResponse | null>(null);

  useEffect(() => {
    let cancelled = false;
    setStatus('loading');
    setEffect(null);
    getRuleEffect(advice.rule_id, advice.suggested_param)
      .then((res) => {
        if (!cancelled) { setEffect(res); setStatus('ready'); }
      })
      .catch(() => {
        if (!cancelled) setStatus('error');
      });
    return () => { cancelled = true; };
  }, [advice.rule_id, advice.suggested_param, getRuleEffect]);

  const title = ADVICE_TITLE[advice.rule_id];
  // 매핑 안 된 규칙(방어적 — 지금 백엔드는 2종만 보냄)은 문구를 지어내지 않고 숨긴다.
  if (!title) return null;
  // 다른 경로(설정 화면)로 이미 켜둔 규칙이면 "켜보라"는 제안 자체가 의미 없다.
  if (status === 'ready' && effect?.currently_enabled) return null;

  const before = status === 'ready' ? effect?.summary.before ?? null : null;
  const showPreview = !!before && before.n_trades > 0 && before.violation_rate != null;

  return (
    <GradientCard colors={[C.blueLight, C.card]} style={styles.card}>
      <View style={styles.colorBar} />
      <View style={styles.top}>
        <View style={styles.icon}>
          <IconLightbulb color={ACCENT} size={22} />
        </View>
        <View style={{ flex: 1 }}>
          <Text style={styles.eyebrow}>AI 맞춤 제안</Text>
          <Text style={styles.title}>{title}</Text>
        </View>
      </View>
      <AdviceBody advice={advice} />
      {showPreview && before && (
        <View style={styles.preview}>
          <IconSearch color="#3454a6" size={14} />
          {before.violation_rate === 0 ? (
            <Text style={styles.previewText}>
              이 기준으로 지난 {before.n_trades}건을 다시 봐도,{'\n'}{NO_VIOLATION_PHRASE[advice.rule_id]} 없었어요
            </Text>
          ) : (
            <Text style={styles.previewText}>
              이 기준으로 지난 거래를 다시 보면, {before.n_trades}건 중{'\n'}
              <Text style={styles.previewBold}>{Math.round((before.violation_rate ?? 0) * 100)}%</Text>가 {VIOLATION_PHRASE[advice.rule_id]} 거예요
            </Text>
          )}
        </View>
      )}
      <Pressable
        onPress={() => goToRulesSettings({ recommendedRuleId: advice.rule_id, recommendedParam: advice.suggested_param })}
      >
        <Text style={styles.link}>규칙 켜기 →</Text>
      </Pressable>
      {disclaimer && <Text style={styles.disclaimer}>{disclaimer}</Text>}
    </GradientCard>
  );
}

const styles = StyleSheet.create({
  card: { paddingLeft: CARD_PADDING + 5, overflow: 'hidden' },
  colorBar: { position: 'absolute', left: 0, top: 0, bottom: 0, width: 4, backgroundColor: C.blue },
  top: { flexDirection: 'row', gap: 9, alignItems: 'flex-start' },
  icon: { width: 34, height: 34, alignItems: 'center', justifyContent: 'center' },
  eyebrow: { fontSize: 11, fontWeight: '700', color: C.blue, letterSpacing: 0.2, marginBottom: 2 },
  title: { fontSize: 16, fontWeight: '700', color: C.navy, letterSpacing: -0.2 },
  body: { fontSize: 14, color: C.navy, lineHeight: 20, marginTop: 10, marginBottom: 9 },
  bodyBold: { fontWeight: '700' },
  preview: {
    flexDirection: 'row', alignItems: 'center', gap: 7,
    backgroundColor: 'rgba(255,255,255,0.6)', borderRadius: 10, padding: 10, marginBottom: 10,
  },
  previewText: { flex: 1, fontSize: 12, color: '#3454a6', lineHeight: 17 },
  previewBold: { fontWeight: '700', color: C.blue },
  link: { fontSize: 13, fontWeight: '600', color: C.blue, textAlign: 'right' },
  disclaimer: { fontSize: 10.5, color: C.muted, lineHeight: 15, marginTop: 11 },
});
