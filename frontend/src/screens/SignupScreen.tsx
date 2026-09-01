import React, { useState } from 'react';
import { View, Text, Pressable, StyleSheet } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { AuthScreen } from '../components/AuthScreen';
import { AuthInput, PasswordInput, ErrorText, CtaButton } from '../components/AuthField';
import { IconTick } from '../assets/icons';
import { C } from '../theme/tokens';
import { useAppState } from '../state/AppState';
import type { AuthStackParamList } from '../navigation/types';

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

const TERMS_ROWS = [
  { label: '(필수) 서비스 이용약관 동의', required: true, legal: 'terms' as const },
  { label: '(필수) 개인정보 수집·이용 동의', required: true, legal: 'privacy' as const },
  { label: '(필수) 만 14세 이상입니다', required: true, legal: null },
  { label: '(선택) 마케팅 정보 수신 동의', required: false, legal: null },
];

function strength(pw: string) {
  if (!pw) return 0;
  let score = 0;
  if (pw.length >= 8) score++;
  if (/[a-zA-Z]/.test(pw) && /[0-9]/.test(pw)) score++;
  if (/[^a-zA-Z0-9]/.test(pw)) score++;
  return score;
}
const STRENGTH_META = [null, { label: '약함', color: '#dc2626' }, { label: '보통', color: '#FFB800' }, { label: '안전', color: '#00C807' }];

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
  const sc = strength(pw);
  const meta = STRENGTH_META[sc];
  const pw2Mismatch = pw2.length > 0 && pw !== pw2;
  const allTerms = terms.every(Boolean);

  const toggleTerm = (i: number) => setTerms((prev) => prev.map((v, idx) => (idx === i ? !v : v)));
  const toggleAll = () => setTerms((prev) => (allTerms ? prev.map(() => false) : prev.map(() => true)));

  const canSubmit = name.trim().length > 0 && suVerified && pw.length > 0 && pw === pw2 && terms[0] && terms[1] && terms[2];

  return (
    <AuthScreen back>
      <Text style={styles.title}>회원가입</Text>
      <Text style={styles.subtitle}>기본 정보를 입력해주세요</Text>

      <View style={{ marginTop: 32, gap: 22 }}>
        <AuthInput label="닉네임" value={name} onChangeText={setName} placeholder="앱에서 사용할 이름" />

        <View>
          <Text style={styles.fieldLabel}>이메일</Text>
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
              disabled={!emailValid && !suVerified}
              onPress={() => navigation.navigate('Verify', { mode: 'signup' })}
              style={[styles.verifyBtn, (emailValid || suVerified) ? styles.verifyBtnActive : styles.verifyBtnInactive]}
            >
              <Text style={{ fontSize: 15, fontWeight: '600', color: suVerified ? C.blue : emailValid ? '#fff' : '#94a3b8' }}>
                {suVerified ? '인증 완료' : '인증하기'}
              </Text>
            </Pressable>
          </View>
          {suVerified && <Text style={styles.verifiedNote}>이메일 인증이 완료되었어요</Text>}
        </View>

        <View>
          <PasswordInput
            label="비밀번호"
            value={pw}
            onChangeText={setPw}
            placeholder="영문·숫자·특수문자 8자 이상"
            show={showPw}
            onToggleShow={() => setShowPw((v) => !v)}
          />
          {meta && <Text style={[styles.strengthText, { color: meta.color }]}>비밀번호 강도: {meta.label}</Text>}
        </View>

        <View>
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

        <View>
          <Text style={styles.fieldLabel}>약관 동의</Text>
          <View style={styles.termsCard}>
          <View style={styles.termsHead}>
            <Text style={styles.termsHeadLabel}>전체 동의</Text>
            <Pressable onPress={toggleAll} style={[styles.roundCheck, allTerms && styles.roundCheckOn]}>
              {allTerms && <IconTick size={11} />}
            </Pressable>
          </View>
          {TERMS_ROWS.map((row, i) => (
            <View key={row.label} style={[styles.termRow, i > 0 && styles.termDivider]}>
              <Pressable onPress={() => toggleTerm(i)} style={styles.termLeft}>
                <View style={[styles.termCheck, terms[i] && styles.termCheckOn]}>
                  {terms[i] && <IconTick size={10} />}
                </View>
                <Text style={styles.termLabel}>{row.label}</Text>
              </Pressable>
              {row.legal && (
                <Pressable onPress={() => navigation.navigate('Legal', { kind: row.legal! })}>
                  <Text style={styles.termView}>보기</Text>
                </Pressable>
              )}
            </View>
          ))}
          </View>
        </View>

        <CtaButton label="가입하기" active={canSubmit} onPress={() => navigation.navigate('SignupDone')} />

        <View style={{ gap: 10, marginTop: 4 }}>
          <Pressable style={styles.socialBtn} onPress={() => navigation.navigate('SocialExtra')}>
            <Text style={styles.socialText}>Google로 계속하기</Text>
          </Pressable>
          <Pressable style={[styles.socialBtn, styles.naverBtn]} onPress={() => navigation.navigate('SocialExtra')}>
            <Text style={[styles.socialText, { color: '#fff' }]}>네이버로 계속하기</Text>
          </Pressable>
        </View>
      </View>
    </AuthScreen>
  );
}

const styles = StyleSheet.create({
  title: { fontSize: 25, fontWeight: '600', color: C.navy, letterSpacing: -0.3 },
  subtitle: { fontSize: 15, color: '#94a3b8', marginTop: 7 },
  fieldLabel: { fontSize: 15, fontWeight: '600', color: C.navy, marginBottom: 10, paddingLeft: 2 },
  emailRow: { flexDirection: 'row', gap: 8, alignItems: 'flex-start' },
  verifyBtn: { borderRadius: 16, paddingVertical: 14, paddingHorizontal: 16, justifyContent: 'center' },
  verifyBtnActive: { backgroundColor: C.blue },
  verifyBtnInactive: { backgroundColor: '#f1f5f9' },
  verifiedNote: { fontSize: 12, color: C.blue, marginTop: 6 },
  strengthText: { fontSize: 12, marginTop: 6 },
  termsCard: { backgroundColor: '#fff', borderRadius: 20, paddingVertical: 14, paddingHorizontal: 16 },
  termsHead: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingBottom: 10 },
  termsHeadLabel: { fontSize: 15, fontWeight: '600', color: C.navy },
  roundCheck: { width: 17, height: 17, borderRadius: 9, borderWidth: 1.5, borderColor: '#e8edf4', alignItems: 'center', justifyContent: 'center' },
  roundCheckOn: { backgroundColor: C.blue, borderColor: C.blue },
  termRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingVertical: 11 },
  termDivider: { borderTopWidth: 1, borderTopColor: C.border },
  termLeft: { flexDirection: 'row', alignItems: 'center', gap: 9, flex: 1 },
  termCheck: { width: 18, height: 18, borderRadius: 9, backgroundColor: '#f1f5f9', alignItems: 'center', justifyContent: 'center' },
  termCheckOn: { backgroundColor: C.blue },
  termLabel: { fontSize: 15, color: C.navy },
  termView: { fontSize: 12, color: '#cbd5e1', textDecorationLine: 'underline' },
  socialBtn: { backgroundColor: '#fff', borderRadius: 16, paddingVertical: 14, alignItems: 'center' },
  naverBtn: { backgroundColor: '#03C75A' },
  socialText: { fontSize: 16, fontWeight: '500', color: C.navy },
});
