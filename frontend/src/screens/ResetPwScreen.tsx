import React, { useState } from 'react';
import { View } from 'react-native';
import { useNavigation, useRoute, RouteProp } from '@react-navigation/native';
import { AuthScreen } from '../components/AuthScreen';
import { PasswordInput, ErrorText, CtaButton, AuthTitle, AuthSubtitle, PasswordStrengthHint, FIELD_GAP, HINT_GAP } from '../components/AuthField';
import { useAppState } from '../state/AppState';
import type { AuthStackParamList } from '../navigation/types';

export function ResetPwScreen() {
  const navigation = useNavigation<any>();
  const route = useRoute<RouteProp<AuthStackParamList, 'ResetPw'>>();
  const { email, code } = route.params;
  const { confirmPasswordReset } = useAppState();
  const [pw, setPw] = useState('');
  const [pw2, setPw2] = useState('');
  const [show1, setShow1] = useState(false);
  const [show2, setShow2] = useState(false);
  const [error, setError] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const mismatch = pw2.length > 0 && pw !== pw2;
  const active = pw.length >= 8 && pw === pw2 && !submitting;

  const onSubmit = async () => {
    if (submitting) return;
    setSubmitting(true);
    try {
      // 코드 유효성은 여기서 새 비밀번호와 함께 서버에 보내야 처음으로 확인됨
      // (코드만 미리 검증하는 API가 없음) — 틀렸으면 여기서 에러가 남.
      await confirmPasswordReset(email, code, pw);
      navigation.popTo('Login');
    } catch (e: any) {
      setError(true);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AuthScreen back>
      <AuthTitle>새 비밀번호 설정</AuthTitle>
      <AuthSubtitle>새로 사용할 비밀번호를 입력해주세요</AuthSubtitle>

      <View style={{ marginTop: 32 }}>
        <PasswordInput
          label="새 비밀번호"
          value={pw}
          onChangeText={(v) => { setPw(v); if (error) setError(false); }}
          placeholder="영문·숫자·특수문자 8자 이상"
          show={show1}
          onToggleShow={() => setShow1((v) => !v)}
        />
        <PasswordStrengthHint pw={pw} />
        <View style={{ marginTop: HINT_GAP }}>
          <PasswordInput
            label="새 비밀번호 확인"
            value={pw2}
            onChangeText={(v) => { setPw2(v); if (error) setError(false); }}
            placeholder="비밀번호 재입력"
            error={mismatch}
            show={show2}
            onToggleShow={() => setShow2((v) => !v)}
          />
          <ErrorText>{mismatch ? '비밀번호가 일치하지 않아요' : error ? '인증코드가 만료되었거나 올바르지 않아요. 처음부터 다시 시도해주세요.' : null}</ErrorText>
        </View>
      </View>

      <View style={{ marginTop: 'auto', paddingTop: FIELD_GAP }}>
        <CtaButton label="비밀번호 변경" active={active} onPress={onSubmit} />
      </View>
    </AuthScreen>
  );
}
