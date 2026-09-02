import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { AuthScreen } from '../components/AuthScreen';
import { CtaButton, FIELD_GAP } from '../components/AuthField';
import { IconCheckBig } from '../assets/icons';
import type { AuthStackParamList } from '../navigation/types';

export function SignupDoneScreen() {
  const navigation = useNavigation<NativeStackNavigationProp<AuthStackParamList>>();

  return (
    <AuthScreen>
      <View style={styles.centerGroup}>
        <IconCheckBig size={56} />
        <Text style={styles.title}>가입 완료!</Text>
        <Text style={styles.body}>{'이제 로그인해서\n거래 내역을 분석해보세요.'}</Text>
      </View>
      <View style={{ marginTop: 'auto', paddingTop: FIELD_GAP }}>
        <CtaButton label="로그인하기" active onPress={() => navigation.replace('Login')} />
      </View>
    </AuthScreen>
  );
}

const styles = StyleSheet.create({
  centerGroup: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: 16 },
  title: { fontSize: 27, fontWeight: '700', color: '#111' },
  body: { fontSize: 16, color: '#64748b', lineHeight: 22, textAlign: 'center', marginBottom: 12 },
});
