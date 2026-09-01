import React, { useEffect, useRef } from 'react';
import { View, Text, Pressable, Animated, Easing, StyleSheet } from 'react-native';
import Svg, { Circle, Path } from 'react-native-svg';
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

export function ProgressBody({ title, body }: { title: string; body: string }) {
  return (
    <View style={styles.root}>
      <Spinner />
      <Text style={styles.title}>{title}</Text>
      <Text style={styles.body}>{body}</Text>
    </View>
  );
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
  return (
    <View style={styles.root}>
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
      <Text style={styles.title}>{title}</Text>
      <Text style={styles.body}>{body}</Text>
      <Pressable onPress={onCta} style={styles.ctaBtn}>
        <Text style={styles.ctaText}>{ctaLabel}</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg, alignItems: 'center', justifyContent: 'center', gap: 20, paddingHorizontal: 32 },
  spinner: {
    width: 50.4, height: 50.4, borderRadius: 25.2,
    borderWidth: 3.73, borderColor: '#e8edf4', borderTopColor: C.blue,
  },
  title: { fontSize: 27, fontWeight: '700', color: '#111', textAlign: 'center' },
  body: { fontSize: 16, color: '#64748b', lineHeight: 24.5, textAlign: 'center', minHeight: 49 },
  ctaBtn: {
    width: '100%', backgroundColor: C.blue, borderRadius: 999, paddingVertical: 16, alignItems: 'center', marginTop: 4,
    shadowColor: '#0066FF', shadowOpacity: 0.27, shadowOffset: { width: 0, height: 4 }, shadowRadius: 16, elevation: 8,
  },
  ctaText: { color: '#fff', fontSize: 17, fontWeight: '600' },
});
