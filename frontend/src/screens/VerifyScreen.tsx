import React, { useEffect, useRef, useState } from 'react';
import { View, Text, TextInput, Pressable, StyleSheet } from 'react-native';
import { useNavigation, useRoute, RouteProp } from '@react-navigation/native';
import { AuthScreen } from '../components/AuthScreen';
import { CtaButton, ErrorText, AuthTitle, AuthSubtitle, FIELD_GAP } from '../components/AuthField';
import { C } from '../theme/tokens';
import { useAppState } from '../state/AppState';
import type { AuthStackParamList } from '../navigation/types';

export function VerifyScreen() {
  const navigation = useNavigation<any>();
  const route = useRoute<RouteProp<AuthStackParamList, 'Verify'>>();
  const { mode, email } = route.params;
  const { verifyEmail, resendVerification, requestPasswordReset } = useAppState();
  const [code, setCode] = useState('');
  const [sec, setSec] = useState(179);
  const [error, setError] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const inputRef = useRef<TextInput>(null);

  useEffect(() => {
    const t = setInterval(() => setSec((s) => Math.max(0, s - 1)), 1000);
    return () => clearInterval(t);
  }, []);

  const mm = String(Math.floor(sec / 60)).padStart(2, '0');
  const ss = String(sec % 60).padStart(2, '0');

  const onChangeCode = (v: string) => {
    const digits = v.replace(/[^0-9]/g, '').slice(0, 6);
    setCode(digits);
    if (error) setError(false);
  };

  const onSubmit = async () => {
    if (submitting) return;
    if (mode === 'signup') {
      setSubmitting(true);
      try {
        await verifyEmail(email, code);
        navigation.navigate('SignupDone');
      } catch (e: any) {
        setCode('');
        setError(true);
      } finally {
        setSubmitting(false);
      }
    } else {
      // 'reset'은 코드를 여기서 따로 검증하는 API가 없음 — 형식만 맞으면 다음 화면(새
      // 비밀번호 입력)으로 넘어가고, 실제 코드 유효성은 그 화면의 최종 제출에서 확인됨.
      navigation.navigate('ResetPw', { email, code });
    }
  };

  const resend = async () => {
    setSec(179);
    setCode('');
    setError(false);
    try {
      if (mode === 'signup') await resendVerification(email);
      else await requestPasswordReset(email);
    } catch {
      // 재전송 실패는 조용히 무시 — 타이머는 이미 리셋했고, 사용자는 그냥 다시 눌러볼 수 있음
    }
  };

  return (
    <AuthScreen back>
      <AuthTitle>인증코드 입력</AuthTitle>
      <AuthSubtitle style={{ lineHeight: 20 }}>{email}로{'\n'}6자리 코드를 보냈어요</AuthSubtitle>

      <Pressable style={styles.boxRow} onPress={() => inputRef.current?.focus()}>
        {Array.from({ length: 6 }).map((_, i) => {
          const filled = i < code.length;
          const active = i === code.length;
          const borderColor = error ? '#dc2626' : active ? C.blue : filled ? '#16213b' : '#e8edf4';
          return (
            <View key={i} style={[styles.box, { borderColor }]}>
              <Text style={styles.boxText}>{code[i] || ''}</Text>
            </View>
          );
        })}
        <TextInput
          ref={inputRef}
          value={code}
          onChangeText={onChangeCode}
          keyboardType="number-pad"
          maxLength={6}
          style={styles.hiddenInput}
          autoFocus
        />
      </Pressable>
      <View style={{ marginTop: 11 }}>
        <ErrorText>{error ? '인증코드가 올바르지 않아요. 다시 입력해주세요.' : null}</ErrorText>
      </View>

      <View style={styles.timerRow}>
        <Text style={[styles.timerText, { color: sec > 0 ? '#dc2626' : '#94a3b8' }]}>{mm}:{ss}</Text>
        <Pressable onPress={resend}>
          <Text style={styles.resend}>코드 재전송</Text>
        </Pressable>
      </View>

      <View style={{ marginTop: 'auto', paddingTop: FIELD_GAP }}>
        <CtaButton label="확인" active={code.length === 6 && !submitting} onPress={onSubmit} />
      </View>
    </AuthScreen>
  );
}

const styles = StyleSheet.create({
  boxRow: { flexDirection: 'row', gap: 8, marginTop: 34, position: 'relative' },
  box: {
    flex: 1, aspectRatio: 1 / 1.18, backgroundColor: '#fff', borderRadius: 14,
    borderWidth: 1.5, alignItems: 'center', justifyContent: 'center',
  },
  boxText: { fontSize: 25, fontWeight: '600', color: C.navy },
  hiddenInput: { position: 'absolute', width: '100%', height: '100%', opacity: 0 },
  timerRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginTop: 11 },
  timerText: { fontSize: 15, fontWeight: '600' },
  resend: { fontSize: 13, color: '#64748b', textDecorationLine: 'underline' },
});
