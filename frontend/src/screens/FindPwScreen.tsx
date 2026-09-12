import React, { useState } from 'react';
import { View } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { AuthScreen } from '../components/AuthScreen';
import { AuthInput, CtaButton, ErrorText, AuthTitle, AuthSubtitle, FIELD_GAP } from '../components/AuthField';
import { useAppState } from '../state/AppState';
import type { AuthStackParamList } from '../navigation/types';

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function FindPwScreen() {
  const navigation = useNavigation<NativeStackNavigationProp<AuthStackParamList>>();
  const { requestPasswordReset } = useAppState();
  const [email, setEmail] = useState('');
  const [error, setError] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const emailValid = EMAIL_RE.test(email);

  const onSubmit = async () => {
    if (!emailValid || submitting) return;
    setSubmitting(true);
    try {
      // 이 API는 계정 존재 여부를 노출하지 않으려고 이메일이 있든 없든 항상 200을 준다 —
      // 그래서 여기서 "가입 안 된 이메일"류 에러는 낼 수 없고, 네트워크 오류일 때만 실패.
      await requestPasswordReset(email);
      navigation.navigate('Verify', { mode: 'reset', email });
    } catch (e: any) {
      setError(true);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AuthScreen back>
      <AuthTitle>비밀번호 찾기</AuthTitle>
      <AuthSubtitle>가입한 이메일로 인증코드를 보내드려요</AuthSubtitle>
      <View style={{ marginTop: 32 }}>
        <AuthInput
          label="이메일"
          value={email}
          onChangeText={(v) => { setEmail(v); if (error) setError(false); }}
          placeholder="name@email.com"
          keyboardType="email-address"
          error={error}
        />
        <ErrorText>{error ? '코드 전송에 실패했어요. 잠시 후 다시 시도해주세요.' : null}</ErrorText>
      </View>
      <View style={{ marginTop: 'auto', paddingTop: FIELD_GAP }}>
        <CtaButton label="인증코드 받기" active={emailValid && !submitting} onPress={onSubmit} />
      </View>
    </AuthScreen>
  );
}
