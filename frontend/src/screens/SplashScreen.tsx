import React, { useEffect } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { LogoStacked } from '../assets/LogoStacked';
import { C } from '../theme/tokens';
import type { AuthStackParamList } from '../navigation/types';

// 앱 최초 진입 시 로그인 상태 확인 중에도(App.tsx) 재사용하는 순수 비주얼.
export function SplashVisual() {
  return (
    <View style={styles.root}>
      <LogoStacked />
      <Text style={styles.caption}>숫자 너머의 나를 분석하다</Text>
    </View>
  );
}

export function SplashScreen() {
  const navigation = useNavigation<NativeStackNavigationProp<AuthStackParamList>>();

  useEffect(() => {
    const t = setTimeout(() => navigation.replace('Login'), 1500);
    return () => clearTimeout(t);
  }, [navigation]);

  return <SplashVisual />;
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg, alignItems: 'center', justifyContent: 'center', gap: 22 },
  caption: { fontSize: 16, color: '#94a3b8' },
});
