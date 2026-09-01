import React, { useState } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { AuthScreen } from '../components/AuthScreen';
import { AuthInput, CtaButton } from '../components/AuthField';
import { C } from '../theme/tokens';
import type { AuthStackParamList } from '../navigation/types';

export function FindPwScreen() {
  const navigation = useNavigation<NativeStackNavigationProp<AuthStackParamList>>();
  const [email, setEmail] = useState('');

  return (
    <AuthScreen back>
      <Text style={styles.title}>비밀번호 찾기</Text>
      <Text style={styles.subtitle}>가입한 이메일로 인증코드를 보내드려요</Text>
      <View style={{ marginTop: 32 }}>
        <AuthInput label="이메일" value={email} onChangeText={setEmail} placeholder="name@email.com" keyboardType="email-address" />
      </View>
      <View style={{ marginTop: 24 }}>
        <CtaButton
          label="인증코드 받기"
          active={email.length > 0}
          onPress={() => navigation.navigate('Verify', { mode: 'reset' })}
        />
      </View>
    </AuthScreen>
  );
}

const styles = StyleSheet.create({
  title: { fontSize: 25, fontWeight: '600', color: C.navy, letterSpacing: -0.3 },
  subtitle: { fontSize: 15, color: '#94a3b8', marginTop: 7 },
});
