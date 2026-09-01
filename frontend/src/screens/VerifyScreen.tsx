import React, { useEffect, useRef, useState } from 'react';
import { View, Text, TextInput, Pressable, StyleSheet } from 'react-native';
import { useNavigation, useRoute } from '@react-navigation/native';
import { AuthScreen } from '../components/AuthScreen';
import { CtaButton } from '../components/AuthField';
import { C } from '../theme/tokens';
import { useAppState } from '../state/AppState';

const CORRECT_CODE = '123456';

export function VerifyScreen() {
  const navigation = useNavigation<any>();
  const route = useRoute<any>();
  const mode: 'signup' | 'reset' | 'changePw' = route.params?.mode || 'signup';
  const { setSuVerified } = useAppState();
  const [code, setCode] = useState('');
  const [sec, setSec] = useState(179);
  const [error, setError] = useState(false);
  const inputRef = useRef<TextInput>(null);

  useEffect(() => {
    const t = setInterval(() => setSec((s) => Math.max(0, s - 1)), 1000);
    return () => clearInterval(t);
  }, []);

  const mm = String(Math.floor(sec / 60)).padStart(2, '0');
  const ss = String(sec % 60).padStart(2, '0');

  const email = mode === 'signup' ? '입력하신 이메일' : '가입하신 이메일';

  const onChangeCode = (v: string) => {
    const digits = v.replace(/[^0-9]/g, '').slice(0, 6);
    setCode(digits);
    if (error) setError(false);
  };

  const onSubmit = () => {
    if (code !== CORRECT_CODE) {
      setCode('');
      setError(true);
      return;
    }
    if (mode === 'signup') {
      setSuVerified(true);
      navigation.navigate('Signup');
    } else if (mode === 'reset') {
      navigation.navigate('ResetPw', { mode: 'reset' });
    } else {
      navigation.navigate('ProfileResetPw', { mode: 'changePw' });
    }
  };

  const resend = () => {
    setSec(179);
    setCode('');
    setError(false);
  };

  return (
    <AuthScreen back>
      <Text style={styles.title}>인증코드 입력</Text>
      <Text style={styles.subtitle}>{email}로{'\n'}6자리 코드를 보냈어요</Text>

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
      <Text style={styles.errorText}>{error ? '인증코드가 올바르지 않아요. 다시 입력해주세요.' : ''}</Text>

      <View style={styles.timerRow}>
        <Text style={[styles.timerText, { color: sec > 0 ? '#dc2626' : '#94a3b8' }]}>{mm}:{ss}</Text>
        <Pressable onPress={resend}>
          <Text style={styles.resend}>코드 재전송</Text>
        </Pressable>
      </View>

      <View style={{ marginTop: 24 }}>
        <CtaButton label="확인" active={code.length === 6} onPress={onSubmit} />
      </View>
    </AuthScreen>
  );
}

const styles = StyleSheet.create({
  title: { fontSize: 25, fontWeight: '600', color: C.navy, letterSpacing: -0.3 },
  subtitle: { fontSize: 15, color: '#94a3b8', marginTop: 8, lineHeight: 20 },
  boxRow: { flexDirection: 'row', gap: 8, marginTop: 34, position: 'relative' },
  box: {
    flex: 1, aspectRatio: 1 / 1.18, backgroundColor: '#fff', borderRadius: 14,
    borderWidth: 1.5, alignItems: 'center', justifyContent: 'center',
  },
  boxText: { fontSize: 25, fontWeight: '600', color: C.navy },
  hiddenInput: { position: 'absolute', width: '100%', height: '100%', opacity: 0 },
  errorText: { fontSize: 13, color: '#dc2626', minHeight: 18, marginTop: 8 },
  timerRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginTop: 6 },
  timerText: { fontSize: 15, fontWeight: '600' },
  resend: { fontSize: 13, color: '#64748b', textDecorationLine: 'underline' },
});
