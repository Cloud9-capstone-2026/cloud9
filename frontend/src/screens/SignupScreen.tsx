import React, { useState } from 'react';
import { View, Text, Pressable, StyleSheet } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { AuthScreen } from '../components/AuthScreen';
import { AuthInput, PasswordInput, ErrorText, CtaButton, SocialButton, AuthTitle, AuthSubtitle, FieldLabel, PasswordStrengthHint, FIELD_GAP, HINT_GAP } from '../components/AuthField';
import { TermsAgreement } from '../components/TermsAgreement';
import { C } from '../theme/tokens';
import { useAppState } from '../state/AppState';
import type { AuthStackParamList } from '../navigation/types';

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function SignupScreen() {
  const navigation = useNavigation<NativeStackNavigationProp<AuthStackParamList>>();
  const { signup } = useAppState();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [pw, setPw] = useState('');
  const [pw2, setPw2] = useState('');
  const [showPw, setShowPw] = useState(false);
  const [showPw2, setShowPw2] = useState(false);
  const [terms, setTerms] = useState([false, false, false, false]);
  const [emailError, setEmailError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const emailValid = EMAIL_RE.test(email);
  const pw2Mismatch = pw2.length > 0 && pw !== pw2;
  const allTerms = terms.every(Boolean);

  const toggleTerm = (i: number) => setTerms((prev) => prev.map((v, idx) => (idx === i ? !v : v)));
  const toggleAll = () => setTerms((prev) => (allTerms ? prev.map(() => false) : prev.map(() => true)));

  const canSubmit = name.trim().length > 0 && emailValid && pw.length > 0 && pw === pw2 && terms[0] && terms[1] && terms[2] && !submitting;

  const onSubmit = async () => {
    if (!canSubmit) return;
    setSubmitting(true);
    setEmailError(null);
    try {
      // 가입 시점에 계정이 바로 생성되고 인증 코드가 발송됨 — 인증은 그다음 화면에서.
      await signup({ email, password: pw, name: name.trim(), agreedTerms: true });
      navigation.navigate('Verify', { mode: 'signup', email });
    } catch (e: any) {
      setEmailError(e?.response?.data?.detail || '가입에 실패했어요. 잠시 후 다시 시도해주세요.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AuthScreen back onBack={() => navigation.goBack()}>
      <AuthTitle>회원가입</AuthTitle>
      <AuthSubtitle>기본 정보를 입력해주세요</AuthSubtitle>

      <View style={{ marginTop: 32 }}>
        <AuthInput label="닉네임" value={name} onChangeText={setName} placeholder="앱에서 사용할 이름" />

        <View style={{ marginTop: FIELD_GAP }}>
          <FieldLabel>이메일</FieldLabel>
          <AuthInput
            value={email}
            onChangeText={(v) => { setEmail(v); if (emailError) setEmailError(null); }}
            placeholder="name@email.com"
            keyboardType="email-address"
            error={!!emailError}
          />
          <ErrorText>{emailError}</ErrorText>
        </View>

        <View style={{ marginTop: HINT_GAP }}>
          <PasswordInput
            label="비밀번호"
            value={pw}
            onChangeText={setPw}
            placeholder="영문·숫자·특수문자 8자 이상"
            show={showPw}
            onToggleShow={() => setShowPw((v) => !v)}
          />
          <PasswordStrengthHint pw={pw} />
        </View>

        <View style={{ marginTop: HINT_GAP }}>
          <PasswordInput
            label="비밀번호 확인"
            value={pw2}
            onChangeText={setPw2}
            placeholder="비밀번호 재입력"
            error={pw2Mismatch}
            show={showPw2}
            onToggleShow={() => setShowPw2((v) => !v)}
          />
          <ErrorText>{pw2Mismatch ? '비밀번호가 일치하지 않아요' : null}</ErrorText>
        </View>

        <View style={{ marginTop: HINT_GAP }}>
          <TermsAgreement terms={terms} onToggleTerm={toggleTerm} onToggleAll={toggleAll} />
        </View>

        <View style={{ marginTop: FIELD_GAP }}>
          <CtaButton label="가입하기" active={canSubmit} onPress={onSubmit} />
        </View>

        <View style={[styles.dividerRow, { marginTop: FIELD_GAP }]}>
          <View style={styles.dividerLine} />
          <Text style={styles.dividerText}>소셜 계정으로 가입</Text>
          <View style={styles.dividerLine} />
        </View>

        <View style={{ gap: 10, marginTop: FIELD_GAP }}>
          <SocialButton provider="google" label="Google로 가입하기" onPress={() => navigation.navigate('SocialExtra')} />
          <SocialButton provider="naver" label="네이버로 가입하기" onPress={() => navigation.navigate('SocialExtra')} />
        </View>
      </View>
    </AuthScreen>
  );
}

const styles = StyleSheet.create({
  dividerRow: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  dividerLine: { flex: 1, height: 1, backgroundColor: C.border },
  dividerText: { fontSize: 13, color: '#94a3b8' },
});
