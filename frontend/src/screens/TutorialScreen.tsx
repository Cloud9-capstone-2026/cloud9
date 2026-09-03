import React from 'react';
import { View, Text, Pressable, StyleSheet } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { C, shadow } from '../theme/tokens';
import { CtaButton } from '../components/AuthField';
import { TUT } from '../data/mock';
import { useAppState } from '../state/AppState';
import type { OnboardingStackParamList } from '../navigation/types';

function ArrowLeft({ size = 18 }: { size?: number }) {
  return <Text style={{ fontSize: size, color: C.navy }}>‹</Text>;
}
function ArrowRight({ size = 18, color = C.navy }: { size?: number; color?: string }) {
  return <Text style={{ fontSize: size, color }}>›</Text>;
}

export function TutorialScreen() {
  const navigation = useNavigation<NativeStackNavigationProp<OnboardingStackParamList>>();
  const { tutStep, setTutStep, rulesConfirmed, ruleSnap } = useAppState();
  const isLast = tutStep === 4;
  const step = Math.min(tutStep, 3);
  const t = TUT[step];

  const nextEnabled = tutStep !== 3 || rulesConfirmed;

  const goPrev = () => setTutStep(Math.max(0, tutStep - 1));
  const goNext = () => { if (nextEnabled) setTutStep(Math.min(4, tutStep + 1)); };

  return (
    <View style={styles.root}>
      {!isLast ? (
        <View style={styles.body}>
          <View style={styles.kickerRow}>
            <Text style={styles.kicker}>Tutorial </Text>
            <View style={styles.kickerNumWrap}>
              <Text style={styles.kicker}>{'0' + (step + 1)}</Text>
              <View style={styles.kickerUnderline} />
            </View>
          </View>
          <Text style={styles.title}>{t.title}</Text>
          <Text style={styles.desc}>{t.body}</Text>
        </View>
      ) : (
        <View style={styles.body}>
          <View style={styles.kickerRow}>
            <Text style={styles.kicker}>Tutorial </Text>
            <View style={styles.kickerNumWrap}>
              <Text style={styles.kicker}>05</Text>
              <View style={styles.kickerUnderline} />
            </View>
          </View>
          <Text style={styles.title}>마지막 단계예요</Text>
          <Text style={styles.desc}>{'20문항 자가진단으로 \n내 투자 성향의 기준점을 만들어요.'}</Text>
        </View>
      )}

      {tutStep > 0 && (
        <Pressable onPress={goPrev} style={[styles.navBtn, styles.navBtnLeft, shadow.header]}>
          <ArrowLeft />
        </Pressable>
      )}
      {!isLast && (
        <Pressable
          onPress={goNext}
          disabled={!nextEnabled}
          style={[styles.navBtn, styles.navBtnRight, shadow.header, !nextEnabled && styles.navBtnDisabled]}
        >
          <ArrowRight color={nextEnabled ? C.navy : '#c3cbd6'} />
        </Pressable>
      )}

      <View style={styles.dotsRow}>
        {[0, 1, 2, 3, 4].map((i) => (
          <View key={i} style={[styles.dot, { width: i === tutStep ? 20 : 6, backgroundColor: i === tutStep ? C.blue : '#d8dfe8' }]} />
        ))}
      </View>

      {step === 3 && !isLast && (
        <View style={styles.ctaWrap}>
          <CtaButton
            label="규칙 정하기"
            active
            onPress={() => { ruleSnap(); navigation.navigate('TutRulesEdit'); }}
          />
        </View>
      )}
      {isLast && (
        <View style={styles.ctaWrap}>
          <CtaButton label="검사 시작하기" active onPress={() => navigation.navigate('OnboardingDiagnosis')} />
        </View>
      )}
      {isLast && (
        <Text style={styles.bottomNote}>검사를 마치면 앱을 바로 시작할 수 있어요</Text>
      )}
    </View>
  );
}

// The CTA button ("규칙 정하기" / "검사 시작하기") always sits at the same
// fixed distance from the bottom, whether or not the trailing note is shown
// below it on the last step — so the button never shifts between steps.
const CTA_BOTTOM = 32;
const CTA_HEIGHT = 54;
const DOTS_GAP = 18;
const NOTE_BOTTOM = 8;

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  body: { position: 'absolute', left: 66, right: 66, top: 250 },
  kickerRow: { flexDirection: 'row' },
  kicker: { fontSize: 13, fontWeight: '600', color: C.blue },
  kickerNumWrap: {},
  kickerUnderline: { height: 1.5, borderRadius: 1, backgroundColor: C.blue, marginTop: 3 },
  title: { fontSize: 34, fontWeight: '700', color: '#111', lineHeight: 40, letterSpacing: -0.4, marginTop: 10 },
  desc: { fontSize: 16, color: '#64748b', lineHeight: 24.5, marginTop: 16 },
  navBtn: {
    position: 'absolute', top: '50%', marginTop: -20, width: 40, height: 40, borderRadius: 20,
    backgroundColor: '#fff', alignItems: 'center', justifyContent: 'center',
  },
  navBtnLeft: { left: 10 },
  navBtnRight: { right: 10 },
  navBtnDisabled: { backgroundColor: '#eef1f5' },
  dotsRow: {
    position: 'absolute', left: 0, right: 0, bottom: CTA_BOTTOM + CTA_HEIGHT + DOTS_GAP,
    flexDirection: 'row', justifyContent: 'center', gap: 6,
  },
  dot: { height: 6, borderRadius: 3 },
  ctaWrap: { position: 'absolute', left: 22, right: 22, bottom: CTA_BOTTOM },
  bottomNote: { position: 'absolute', left: 22, right: 22, bottom: NOTE_BOTTOM, fontSize: 13, color: '#94a3b8', textAlign: 'center' },
});
