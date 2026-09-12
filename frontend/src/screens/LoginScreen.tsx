import React, { useState } from 'react';
import { View, Text, Pressable, StyleSheet } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { AuthScreen } from '../components/AuthScreen';
import { AuthInput, PasswordInput, ErrorText, CtaButton, SocialButton, AuthTitle, AuthSubtitle, HINT_GAP } from '../components/AuthField';
import { Logo } from '../assets/Logo';
import { IconTick } from '../assets/icons';
import { C } from '../theme/tokens';
import { useAppState } from '../state/AppState';
import type { AuthStackParamList } from '../navigation/types';

export function LoginScreen() {
  const navigation = useNavigation<NativeStackNavigationProp<AuthStackParamList>>();
  const { login, keepLogin, setKeepLogin } = useAppState();
  const [email, setEmail] = useState('');
  const [pw, setPw] = useState('');
  const [showPw, setShowPw] = useState(false);
  // 백엔드가 이메일/비번 오류를 401 하나로 통일해서 내려줘서(어느 쪽이 틀렸는지 구분 불가),
  // 어느 필드가 문제인지 나눠 보여주는 대신 두 필드 모두 에러 표시 + 공통 문구 하나로 처리.
  const [error, setError] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const onSubmit = async () => {
    if (submitting) return;
    setSubmitting(true);
    try {
      await login(email, pw);
    } catch (e: any) {
      setError(true);
      setPw('');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AuthScreen>
      <Logo />
      <AuthTitle style={{ marginTop: 26 }}>반갑습니다!</AuthTitle>
      <AuthSubtitle>이메일로 로그인하세요</AuthSubtitle>

      <View style={{ marginTop: 32 }}>
        <View>
          <AuthInput
            label="이메일"
            value={email}
            onChangeText={(v) => { setEmail(v); if (error) setError(false); }}
            placeholder="name@email.com"
            keyboardType="email-address"
            error={error}
          />
          <ErrorText>{null}</ErrorText>
        </View>
        <View style={{ marginTop: HINT_GAP }}>
          <PasswordInput
            label="비밀번호"
            value={pw}
            onChangeText={(v) => { setPw(v); if (error) setError(false); }}
            placeholder="비밀번호 입력"
            show={showPw}
            onToggleShow={() => setShowPw((v) => !v)}
            error={error}
          />
          <ErrorText>{error ? '이메일 또는 비밀번호가 올바르지 않아요. 다시 확인해주세요.' : null}</ErrorText>
        </View>
      </View>

      <View style={styles.rowBetween}>
        <Pressable onPress={() => setKeepLogin(!keepLogin)} style={styles.keepRow}>
          <View style={[styles.checkbox, keepLogin && styles.checkboxOn]}>
            {keepLogin && <IconTick size={11} />}
          </View>
          <Text style={styles.keepLabel}>로그인 상태 유지</Text>
        </Pressable>
        <Pressable onPress={() => navigation.navigate('FindPw')}>
          <Text style={styles.link}>비밀번호를 잊으셨나요?</Text>
        </Pressable>
      </View>

      <View style={{ marginTop: 20 }}>
        <CtaButton label="로그인" active={!submitting} onPress={onSubmit} />
      </View>

      <View style={styles.dividerRow}>
        <View style={styles.dividerLine} />
        <Text style={styles.dividerText}>또는</Text>
        <View style={styles.dividerLine} />
      </View>

      <View style={{ gap: 10 }}>
        <SocialButton provider="google" label="Google로 계속하기" onPress={() => navigation.navigate('SocialExtra')} />
        <SocialButton provider="naver" label="네이버로 계속하기" onPress={() => navigation.navigate('SocialExtra')} />
      </View>

      <View style={styles.bottomRow}>
        <Text style={styles.bottomText}>아직 회원이 아니신가요? </Text>
        <Pressable onPress={() => navigation.navigate('Signup')}>
          <Text style={styles.bottomLink}>회원가입</Text>
        </Pressable>
      </View>
    </AuthScreen>
  );
}

const styles = StyleSheet.create({
  rowBetween: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginTop: 10 },
  keepRow: { flexDirection: 'row', alignItems: 'center', gap: 7 },
  checkbox: {
    width: 18, height: 18, borderRadius: 6, borderWidth: 1.5, borderColor: '#e8edf4',
    backgroundColor: '#fff', alignItems: 'center', justifyContent: 'center',
  },
  checkboxOn: { backgroundColor: C.blue, borderColor: C.blue },
  keepLabel: { fontSize: 13, color: '#64748b' },
  link: { fontSize: 13, color: '#64748b' },
  dividerRow: { flexDirection: 'row', alignItems: 'center', gap: 10, marginTop: 35, marginBottom: 22 },
  dividerLine: { flex: 1, height: 1, backgroundColor: C.border },
  dividerText: { fontSize: 13, color: '#94a3b8' },
  bottomRow: { flexDirection: 'row', justifyContent: 'center', marginTop: 'auto', paddingTop: 26 },
  bottomText: { fontSize: 15, color: '#64748b' },
  bottomLink: { fontSize: 15, color: C.blue, fontWeight: '600' },
});
