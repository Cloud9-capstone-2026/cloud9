import React, { useRef, useState } from 'react';
import { View, Text, Pressable, StyleSheet } from 'react-native';
import { Header } from '../components/Header';
import { IconDoc, IconClock, IconClip, IconCheckBig, IconPrev, IconTick } from '../assets/icons';
import { C, ACCENT, shadow } from '../theme/tokens';
import { QUESTIONS } from '../data/mock';
import { goToTab } from '../navigation/navigationRef';

type Phase = 'intro' | 'quiz' | 'done';
const CIRCLE_SIZES = [54, 46, 38, 46, 54];
const TOTAL = QUESTIONS.length;

export function DiagnosisScreen() {
  const [phase, setPhase] = useState<Phase>('intro');
  const [current, setCurrent] = useState(0);
  const [answers, setAnswers] = useState<number[]>(new Array(TOTAL).fill(0));
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const answer = (val: number) => {
    const next = answers.slice();
    next[current] = val;
    setAnswers(next);
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      setCurrent((c) => {
        if (c < TOTAL - 1) return c + 1;
        setPhase('done');
        return c;
      });
    }, 480);
  };

  const goPrev = () => {
    if (current > 0) setCurrent((c) => c - 1);
  };

  return (
    <View style={styles.root}>
      <Header back />
      {phase === 'intro' && (
        <View style={styles.body}>
          <View style={styles.introCenter}>
            <View style={{ marginBottom: 24 }}>
              <IconDoc size={56} />
            </View>
            <Text style={styles.introTitle}>투자 성향 자가진단</Text>
            <Text style={styles.introDesc}>평소 투자할 때의 생각과 습관을{'\n'}솔직하게 답해주세요. 정답은 없어요.</Text>
            <View style={styles.chipsRow}>
              <View style={styles.infoChip}>
                <IconClock size={16} />
                <View>
                  <Text style={styles.infoChipLabel}>예상 소요 시간</Text>
                  <Text style={styles.infoChipValue}>약 3분 소요</Text>
                </View>
              </View>
              <View style={styles.infoChip}>
                <IconClip size={16} />
                <View>
                  <Text style={styles.infoChipLabel}>전체 질문 수</Text>
                  <Text style={styles.infoChipValue}>문항 20개</Text>
                </View>
              </View>
            </View>
          </View>
          <View style={styles.bottomArea}>
            <Pressable
              onPress={() => { setPhase('quiz'); setCurrent(0); setAnswers(new Array(TOTAL).fill(0)); }}
              style={[styles.ctaBtn, shadow.ctaBlue]}
            >
              <Text style={styles.ctaText}>검사 시작하기</Text>
            </Pressable>
            <Text style={styles.ctaSub}>답변은 언제든 다시 검사해서 갱신할 수 있어요</Text>
          </View>
        </View>
      )}

      {phase === 'quiz' && (
        <View style={styles.quizRoot}>
          <View style={styles.quizHeader}>
            <View style={styles.quizProgressRow}>
              <Text style={styles.progressingText}>진행 중</Text>
              <Text style={styles.progressCount}>
                {current + 1}<Text style={styles.progressTotal}>/{TOTAL}</Text>
              </Text>
            </View>
            <View style={styles.progressTrack}>
              <View style={[styles.progressFill, { width: `${((current + 1) / TOTAL) * 100}%` }]} />
            </View>
          </View>

          <View style={styles.quizBody}>
            <Text style={styles.qLabel}>Q{current + 1}</Text>
            <Text style={styles.qText}>{QUESTIONS[current]}</Text>
            <View style={styles.optionsRow}>
              {[1, 2, 3, 4, 5].map((val, i) => {
                const isSel = answers[current] === val;
                const size = CIRCLE_SIZES[i];
                return (
                  <View key={val} style={styles.optionWrap}>
                    <Pressable
                      onPress={() => answer(val)}
                      style={[
                        styles.optionCircle,
                        {
                          width: size, height: size, borderRadius: size / 2,
                          backgroundColor: isSel ? ACCENT : C.card,
                          borderWidth: 1.5, borderColor: isSel ? ACCENT : C.border,
                          transform: [{ scale: isSel ? 1.08 : 1 }],
                        },
                      ]}
                    >
                      {isSel && <IconTick size={Math.round(size * 0.45)} />}
                    </Pressable>
                    <Text style={styles.optionVal}>{val}</Text>
                    {(val === 1 || val === 5) && (
                      <Text style={styles.optionEndLabel}>{val === 1 ? '전혀 아니다' : '매우 그렇다'}</Text>
                    )}
                  </View>
                );
              })}
            </View>
          </View>

          <View style={styles.prevWrap}>
            <Pressable onPress={goPrev} disabled={current === 0} style={styles.prevBtn}>
              <IconPrev enabled={current > 0} size={14} />
              <Text style={{ fontSize: 12, color: current > 0 ? C.muted : C.border }}>이전 문항 다시보기</Text>
            </Pressable>
          </View>
        </View>
      )}

      {phase === 'done' && (
        <View style={styles.body}>
          <View style={styles.introCenter}>
            <View style={{ marginBottom: 24 }}>
              <IconCheckBig size={56} />
            </View>
            <Text style={styles.doneTitle}>검사 완료!</Text>
            <Text style={styles.introDesc}>총 20문항에 모두 답해주셨어요.{'\n'}결과를 분석 중이에요.</Text>
          </View>
          <View style={styles.bottomArea}>
            <Pressable onPress={() => goToTab('MyPage')} style={[styles.ctaBtn, shadow.ctaBlue]}>
              <Text style={styles.ctaText}>성향 분석 보러가기</Text>
            </Pressable>
          </View>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  body: { flex: 1, paddingHorizontal: 28 },
  introCenter: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  introTitle: { fontSize: 26, fontWeight: '700', color: '#111', letterSpacing: -0.6, lineHeight: 34, marginBottom: 12, textAlign: 'center' },
  doneTitle: { fontSize: 24, fontWeight: '700', color: '#111', letterSpacing: -0.5, marginBottom: 10, textAlign: 'center' },
  introDesc: { fontSize: 14, color: C.muted, lineHeight: 24, marginBottom: 36, textAlign: 'center' },
  chipsRow: { flexDirection: 'row', gap: 12 },
  infoChip: { flexDirection: 'row', alignItems: 'center', gap: 7, backgroundColor: C.card, borderRadius: 16, paddingVertical: 10, paddingHorizontal: 16 },
  infoChipLabel: { fontSize: 10, color: C.muted },
  infoChipValue: { fontSize: 12, fontWeight: '600', color: C.navy },
  bottomArea: { paddingVertical: 16, paddingBottom: 28 },
  ctaBtn: { backgroundColor: C.blue, borderRadius: 999, paddingVertical: 17, alignItems: 'center' },
  ctaText: { color: '#fff', fontSize: 16, fontWeight: '600', letterSpacing: -0.2 },
  ctaSub: { textAlign: 'center', fontSize: 12, color: C.muted, marginTop: 10 },
  quizRoot: { flex: 1 },
  quizHeader: { paddingHorizontal: 22, paddingTop: 16, paddingBottom: 12 },
  quizProgressRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 },
  progressingText: { fontSize: 12, color: C.muted },
  progressCount: { fontSize: 13, fontWeight: '600', color: C.navy },
  progressTotal: { fontWeight: '400', color: C.muted },
  progressTrack: { height: 4, backgroundColor: C.mutedBg, borderRadius: 999, overflow: 'hidden' },
  progressFill: { height: '100%', backgroundColor: C.blue, borderRadius: 999 },
  quizBody: { flex: 1, justifyContent: 'center', paddingHorizontal: 28 },
  qLabel: { fontSize: 11, fontWeight: '500', color: C.blue, marginBottom: 16, letterSpacing: 0.8 },
  qText: { fontSize: 19, fontWeight: '600', color: '#111', lineHeight: 30, letterSpacing: -0.3, minHeight: 120, marginBottom: 44 },
  optionsRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', height: 54 },
  optionWrap: { width: 54, height: 54, alignItems: 'center', justifyContent: 'center' },
  optionCircle: { alignItems: 'center', justifyContent: 'center' },
  optionVal: { position: 'absolute', top: 60, fontSize: 10, color: C.muted },
  optionEndLabel: { position: 'absolute', top: 74, fontSize: 10, color: C.muted, width: 80, textAlign: 'center' },
  prevWrap: { paddingHorizontal: 22, paddingVertical: 24, alignItems: 'center' },
  prevBtn: { flexDirection: 'row', alignItems: 'center', gap: 5 },
});
