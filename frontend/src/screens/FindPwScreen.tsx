import React, { useState } from 'react';
import { View } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { AuthScreen } from '../components/AuthScreen';
import { AuthInput, CtaButton, AuthTitle, AuthSubtitle, FIELD_GAP } from '../components/AuthField';
import type { AuthStackParamList } from '../navigation/types';

export function FindPwScreen() {
  const navigation = useNavigation<NativeStackNavigationProp<AuthStackParamList>>();
  const [email, setEmail] = useState('');

  return (
    <AuthScreen back>
      <AuthTitle>비밀번호 찾기</AuthTitle>
      <AuthSubtitle>가입한 이메일로 인증코드를 보내드려요</AuthSubtitle>
      <View style={{ marginTop: 32 }}>
        <AuthInput label="이메일" value={email} onChangeText={setEmail} placeholder="name@email.com" keyboardType="email-address" />
      </View>
      <View style={{ marginTop: 'auto', paddingTop: FIELD_GAP }}>
        <CtaButton
          label="인증코드 받기"
          active={email.length > 0}
          onPress={() => navigation.navigate('Verify', { mode: 'reset' })}
        />
      </View>
    </AuthScreen>
  );
}
