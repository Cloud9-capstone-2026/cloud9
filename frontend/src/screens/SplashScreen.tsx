import React, { useEffect } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { LogoStacked } from '../assets/LogoStacked';
import { C } from '../theme/tokens';
import type { AuthStackParamList } from '../navigation/types';

export function SplashScreen() {
  const navigation = useNavigation<NativeStackNavigationProp<AuthStackParamList>>();

  useEffect(() => {
    const t = setTimeout(() => navigation.replace('Login'), 1500);
    return () => clearTimeout(t);
  }, [navigation]);

  return (
    <View style={styles.root}>
      <LogoStacked />
      <Text style={styles.caption}>숫자 너머의 나를 분석하다</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg, alignItems: 'center', justifyContent: 'center', gap: 22 },
  caption: { fontSize: 16, color: '#94a3b8' },
});
