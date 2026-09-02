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
  const { suVerified, setSuVerified } = useAppState();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [pw, setPw] = useState('');
  const [pw2, setPw2] = useState('');
  const [showPw, setShowPw] = useState(false);
  const [showPw2, setShowPw2] = useState(false);
  const [terms, setTerms] = useState([false, false, false, false]);

  const emailValid = EMAIL_RE.test(email);
  const pw2Mismatch = pw2.length > 0 && pw !== pw2;
  const allTerms = terms.every(Boolean);

  const toggleTerm = (i: number) => setTerms((prev) => prev.map((v, idx) => (idx === i ? !v : v)));
  const toggleAll = () => setTerms((prev) => (allTerms ? prev.map(() => false) : prev.map(() => true)));

  const canSubmit = name.trim().length > 0 && suVerified && pw.length > 0 && pw === pw2 && terms[0] && terms[1] && terms[2];

  return (
    <AuthScreen back onBack={() => { setSuVerified(false); navigation.goBack(); }}>
      <AuthTitle>회원가입</AuthTitle>
      <AuthSubtitle>기본 정보를 입력해주세요</AuthSubtitle>

      <View style={{ marginTop: 32 }}>
        <AuthInput label="닉네임" value={name} onChangeText={setName} placeholder="앱에서 사용할 이름" />

        <View style={{ marginTop: FIELD_GAP }}>
          <FieldLabel>이메일</FieldLabel>
          <View style={styles.emailRow}>
            <View style={{ flex: 1 }}>
              <AuthInput
                value={email}
                onChangeText={setEmail}
                placeholder="name@email.com"
                editable={!suVerified}
                keyboardType="email-address"
              />
            </View>
            <Pressable
              disabled={suVerified || !emailValid}
              onPress={() => navigation.navigate('Verify', { mode: 'signup' })}
              style={[
                styles.verifyBtn,
                suVerified ? styles.verifyBtnDone : emailValid ? styles.verifyBtnActive : styles.verifyBtnInactive,
              ]}
            >
              <Text style={{ fontSize: 15, fontWeight: '600', color: suVerified ? C.blue : emailValid ? '#fff' : '#94a3b8' }}>
                {suVerified ? '인증 완료' : '인증하기'}
              </Text>
            </Pressable>
          </View>
          <ErrorText color={C.blue}>{suVerified ? '이메일 인증이 완료되었어요' : null}</ErrorText>
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
          <CtaButton label="가입하기" active={canSubmit} onPress={() => { setSuVerified(false); navigation.navigate('SignupDone'); }} />
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
  emailRow: { flexDirection: 'row', gap: 8, alignItems: 'flex-start' },
  verifyBtn: { borderRadius: 16, paddingVertical: 17, paddingHorizontal: 16, justifyContent: 'center' },
  verifyBtnActive: { backgroundColor: C.blue },
  verifyBtnInactive: { backgroundColor: '#f1f5f9' },
  verifyBtnDone: { backgroundColor: '#f1f5f9' },
  dividerRow: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  dividerLine: { flex: 1, height: 1, backgroundColor: C.border },
  dividerText: { fontSize: 13, color: '#94a3b8' },
});
