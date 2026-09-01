import React, { useState } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useNavigation, useRoute } from '@react-navigation/native';
import { AuthScreen } from '../components/AuthScreen';
import { PasswordInput, ErrorText, CtaButton } from '../components/AuthField';
import { C } from '../theme/tokens';

export function ResetPwScreen() {
  const navigation = useNavigation<any>();
  const route = useRoute<any>();
  const mode: 'reset' | 'changePw' = route.params?.mode || 'reset';
  const [pw, setPw] = useState('');
  const [pw2, setPw2] = useState('');
  const [show1, setShow1] = useState(false);
  const [show2, setShow2] = useState(false);

  const mismatch = pw2.length > 0 && pw !== pw2;
  const active = pw.length >= 8 && pw === pw2;

  const onSubmit = () => {
    if (mode === 'changePw') navigation.navigate('Profile');
    else navigation.navigate('Login');
  };

  return (
    <AuthScreen back>
      <Text style={styles.title}>새 비밀번호 설정</Text>
      <Text style={styles.subtitle}>새로 사용할 비밀번호를 입력해주세요</Text>

      <View style={{ marginTop: 32, gap: 22 }}>
        <PasswordInput
          label="새 비밀번호"
          value={pw}
          onChangeText={setPw}
          placeholder="영문·숫자·특수문자 8자 이상"
          show={show1}
          onToggleShow={() => setShow1((v) => !v)}
        />
        <View>
          <PasswordInput
            label="새 비밀번호 확인"
            value={pw2}
            onChangeText={setPw2}
            placeholder="비밀번호 재입력"
            error={mismatch}
            show={show2}
            onToggleShow={() => setShow2((v) => !v)}
          />
          <ErrorText>{mismatch ? '비밀번호가 일치하지 않아요' : null}</ErrorText>
        </View>
        <CtaButton label="비밀번호 변경" active={active} onPress={onSubmit} />
      </View>
    </AuthScreen>
  );
}

const styles = StyleSheet.create({
  title: { fontSize: 25, fontWeight: '600', color: C.navy, letterSpacing: -0.3 },
  subtitle: { fontSize: 15, color: '#94a3b8', marginTop: 7 },
});
