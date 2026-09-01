import React from 'react';
import { View, Text, Pressable, StyleSheet } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { IconCheckBig } from '../assets/icons';
import { C } from '../theme/tokens';
import type { AuthStackParamList } from '../navigation/types';

export function SignupDoneScreen() {
  const navigation = useNavigation<NativeStackNavigationProp<AuthStackParamList>>();

  return (
    <View style={styles.root}>
      <IconCheckBig size={56} />
      <Text style={styles.title}>가입 완료!</Text>
      <Text style={styles.body}>{'이제 로그인해서\n거래 내역을 분석해보세요.'}</Text>
      <Pressable onPress={() => navigation.replace('Login')} style={styles.cta}>
        <Text style={styles.ctaText}>로그인하기</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg, alignItems: 'center', justifyContent: 'center', gap: 16, paddingHorizontal: 32 },
  title: { fontSize: 27, fontWeight: '700', color: '#111' },
  body: { fontSize: 16, color: '#64748b', lineHeight: 22, textAlign: 'center', marginBottom: 12 },
  cta: {
    width: '100%', backgroundColor: C.blue, borderRadius: 999, paddingVertical: 16, alignItems: 'center',
    shadowColor: '#0066FF', shadowOpacity: 0.27, shadowOffset: { width: 0, height: 4 }, shadowRadius: 16, elevation: 8,
  },
  ctaText: { color: '#fff', fontSize: 17, fontWeight: '600' },
});
