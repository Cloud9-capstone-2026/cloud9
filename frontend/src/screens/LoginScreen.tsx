import React, { useState } from 'react';
import { View, Text, Pressable, StyleSheet } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { AuthScreen } from '../components/AuthScreen';
import { AuthInput, PasswordInput, CtaButton } from '../components/AuthField';
import { Logo } from '../assets/Logo';
import { IconGoogle, IconNaver, IconTick } from '../assets/icons';
import { C } from '../theme/tokens';
import { useAppState } from '../state/AppState';
import type { AuthStackParamList } from '../navigation/types';

export function LoginScreen() {
  const navigation = useNavigation<NativeStackNavigationProp<AuthStackParamList>>();
  const { login, keepLogin, setKeepLogin } = useAppState();
  const [email, setEmail] = useState('');
  const [pw, setPw] = useState('');
  const [showPw, setShowPw] = useState(false);

  return (
    <AuthScreen>
      <Logo />
      <Text style={styles.title}>반갑습니다!</Text>
      <Text style={styles.subtitle}>이메일로 로그인하세요</Text>

      <View style={{ marginTop: 32, gap: 22 }}>
        <AuthInput
          label="이메일"
          value={email}
          onChangeText={setEmail}
          placeholder="name@email.com"
          keyboardType="email-address"
        />
        <PasswordInput
          label="비밀번호"
          value={pw}
          onChangeText={setPw}
          placeholder="비밀번호 입력"
          show={showPw}
          onToggleShow={() => setShowPw((v) => !v)}
        />
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
        <CtaButton label="로그인" active onPress={login} />
      </View>

      <View style={styles.dividerRow}>
        <View style={styles.dividerLine} />
        <Text style={styles.dividerText}>또는</Text>
        <View style={styles.dividerLine} />
      </View>

      <View style={{ gap: 10 }}>
        <Pressable style={[styles.socialBtn, styles.googleBtn]} onPress={() => navigation.navigate('SocialExtra')}>
          <IconGoogle size={18} />
          <Text style={styles.googleText}>Google로 계속하기</Text>
        </Pressable>
        <Pressable style={[styles.socialBtn, styles.naverBtn]} onPress={() => navigation.navigate('SocialExtra')}>
          <IconNaver size={18} />
          <Text style={styles.naverText}>네이버로 계속하기</Text>
        </Pressable>
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
  title: { fontSize: 25, fontWeight: '600', color: C.navy, letterSpacing: -0.3, marginTop: 26 },
  subtitle: { fontSize: 15, color: '#94a3b8', marginTop: 7 },
  rowBetween: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginTop: 26 },
  keepRow: { flexDirection: 'row', alignItems: 'center', gap: 7 },
  checkbox: {
    width: 18, height: 18, borderRadius: 6, borderWidth: 1.5, borderColor: '#e8edf4',
    backgroundColor: '#fff', alignItems: 'center', justifyContent: 'center',
  },
  checkboxOn: { backgroundColor: C.blue, borderColor: C.blue },
  keepLabel: { fontSize: 13, color: '#64748b' },
  link: { fontSize: 13, color: '#64748b' },
  dividerRow: { flexDirection: 'row', alignItems: 'center', gap: 10, marginTop: 28, marginBottom: 22 },
  dividerLine: { flex: 1, height: 1, backgroundColor: C.border },
  dividerText: { fontSize: 13, color: '#94a3b8' },
  socialBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 9, borderRadius: 16, paddingVertical: 14 },
  googleBtn: {
    backgroundColor: '#fff',
    shadowColor: '#16213b', shadowOpacity: 0.08, shadowOffset: { width: 0, height: 2 }, shadowRadius: 8, elevation: 2,
  },
  googleText: { fontSize: 16, fontWeight: '500', color: C.navy },
  naverBtn: { backgroundColor: '#03C75A' },
  naverText: { fontSize: 16, fontWeight: '500', color: '#fff' },
  bottomRow: { flexDirection: 'row', justifyContent: 'center', marginTop: 26 },
  bottomText: { fontSize: 15, color: '#64748b' },
  bottomLink: { fontSize: 15, color: C.blue, fontWeight: '600' },
});
