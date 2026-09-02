import React, { useEffect, useRef } from 'react';
import { View, Text, Animated, Easing, StyleSheet } from 'react-native';
import Svg, { Circle, Path } from 'react-native-svg';
import { CtaButton } from './AuthField';
import { C } from '../theme/tokens';

export function Spinner() {
  const spin = useRef(new Animated.Value(0)).current;
  useEffect(() => {
    const loop = Animated.loop(
      Animated.timing(spin, { toValue: 1, duration: 800, easing: Easing.linear, useNativeDriver: true })
    );
    loop.start();
    return () => loop.stop();
  }, [spin]);
  const rotate = spin.interpolate({ inputRange: [0, 1], outputRange: ['0deg', '360deg'] });
  return (
    <Animated.View style={[styles.spinner, { transform: [{ rotate }] }]} />
  );
}

// 업로드/분석 진행·완료·실패 6개 화면이 전부 이 레이아웃을 공유함.
// 원(스피너/체크·경고 아이콘) 슬롯과 하단 버튼 슬롯을 항상 같은 크기로 고정해서
// 화면이 전환될 때 원·타이틀·서브타이틀 위치가 들쑥날쑥하지 않게 함
// (버튼이 없는 화면도 투명한 버튼을 그대로 렌더해서 자리만 차지하게 함).
function FlowLayout({
  icon, title, body, cta,
}: {
  icon: React.ReactNode;
  title: string;
  body: string;
  cta?: { label: string; onPress: () => void };
}) {
  return (
    <View style={styles.root}>
      <View style={styles.center}>
        <View style={styles.iconSlot}>{icon}</View>
        <Text style={styles.title}>{title}</Text>
        <Text style={styles.body}>{body}</Text>
      </View>
      <View style={styles.bottomArea}>
        <View style={!cta && styles.ctaHidden} pointerEvents={cta ? 'auto' : 'none'}>
          <CtaButton label={cta?.label ?? ' '} active onPress={cta?.onPress ?? (() => {})} style={styles.ctaRadius} />
        </View>
      </View>
    </View>
  );
}

export function ProgressBody({ title, body }: { title: string; body: string }) {
  return <FlowLayout icon={<Spinner />} title={title} body={body} />;
}

export function ResultBody({
  success, title, body, ctaLabel, onCta,
}: {
  success: boolean;
  title: string;
  body: string;
  ctaLabel: string;
  onCta: () => void;
}) {
  const color = success ? C.blue : '#dc2626';
  const icon = (
    <Svg width={56} height={56} viewBox="0 0 24 24" fill="none">
      <Circle cx={12} cy={12} r={10} stroke={color} strokeWidth={1.6} />
      {success ? (
        <Path d="M7.5 12.4l3.1 3.1 5.9-6.4" stroke={color} strokeWidth={1.9} strokeLinecap="round" strokeLinejoin="round" />
      ) : (
        <>
          <Path d="M12 7.5v5.6" stroke={color} strokeWidth={2} strokeLinecap="round" />
          <Circle cx={12} cy={16.7} r={1.1} fill={color} />
        </>
      )}
    </Svg>
  );
  return <FlowLayout icon={icon} title={title} body={body} cta={{ label: ctaLabel, onPress: onCta }} />;
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg, paddingHorizontal: 32, paddingBottom: 28 },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: 20 },
  iconSlot: { width: 56, height: 56, alignItems: 'center', justifyContent: 'center' },
  spinner: {
    width: 50.4, height: 50.4, borderRadius: 25.2,
    borderWidth: 3.73, borderColor: '#e8edf4', borderTopColor: C.blue,
  },
  title: { fontSize: 27, fontWeight: '700', color: '#111', textAlign: 'center' },
  body: { fontSize: 16, color: '#64748b', lineHeight: 24.5, textAlign: 'center', minHeight: 49 },
  bottomArea: { paddingTop: 16 },
  ctaHidden: { opacity: 0 },
  ctaRadius: { borderRadius: 30 },
});
