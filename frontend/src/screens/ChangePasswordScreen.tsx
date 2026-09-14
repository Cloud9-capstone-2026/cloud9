import React, { useState } from 'react';
import { View, Text, TextInput, Pressable, StyleSheet } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { Screen } from '../components/Screen';
import { IconEye } from '../assets/icons';
import { C, text } from '../theme/tokens';
import { useAppState } from '../state/AppState';

export function ChangePasswordScreen() {
  const navigation = useNavigation();
  const { changePassword } = useAppState();
  const [current, setCurrent] = useState('');
  const [next, setNext] = useState('');
  const [next2, setNext2] = useState('');
  const [showCurrent, setShowCurrent] = useState(false);
  const [showNext, setShowNext] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const mismatch = next2.length > 0 && next !== next2;
  const canSave = current.length > 0 && next.length >= 8 && next === next2 && !submitting;

  const onSave = async () => {
    if (!canSave) return;
    setSubmitting(true);
    setError(null);
    try {
      await changePassword(current, next);
      navigation.goBack();
    } catch (e: any) {
      setError(e?.response?.data?.detail || '비밀번호 변경에 실패했어요.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Screen
      back
      floatingFooter={
        <Pressable onPress={onSave} disabled={!canSave} style={[styles.saveBtn, { backgroundColor: canSave ? C.blue : C.card }]}>
          <Text style={{ color: canSave ? '#fff' : C.muted, fontSize: 17, fontWeight: '600' }}>저장하기</Text>
        </Pressable>
      }
    >
      <Text style={text.screenTitle}>비밀번호 변경</Text>
      <Text style={[text.screenSubtitle, styles.subtitle]}>현재 비밀번호를 확인하고 새 비밀번호로 바꿔요</Text>

      <View style={{ marginTop: 24, gap: 14 }}>
        <View>
          <Text style={styles.label}>현재 비밀번호</Text>
          <View style={styles.inputRow}>
            <TextInput
              value={current}
              onChangeText={(v) => { setCurrent(v); if (error) setError(null); }}
              placeholder="현재 비밀번호"
              placeholderTextColor={C.muted}
              secureTextEntry={!showCurrent}
              style={styles.input}
            />
            <Pressable onPress={() => setShowCurrent((v) => !v)} style={styles.eyeBtn}>
              <IconEye on={showCurrent} size={20} />
            </Pressable>
          </View>
        </View>

        <View>
          <Text style={styles.label}>새 비밀번호</Text>
          <View style={styles.inputRow}>
            <TextInput
              value={next}
              onChangeText={(v) => { setNext(v); if (error) setError(null); }}
              placeholder="영문·숫자·특수문자 8자 이상"
              placeholderTextColor={C.muted}
              secureTextEntry={!showNext}
              style={styles.input}
            />
            <Pressable onPress={() => setShowNext((v) => !v)} style={styles.eyeBtn}>
              <IconEye on={showNext} size={20} />
            </Pressable>
          </View>
        </View>

        <View>
          <Text style={styles.label}>새 비밀번호 확인</Text>
          <TextInput
            value={next2}
            onChangeText={(v) => { setNext2(v); if (error) setError(null); }}
            placeholder="비밀번호 재입력"
            placeholderTextColor={C.muted}
            secureTextEntry={!showNext}
            style={[styles.input, styles.inputPlain, mismatch && styles.inputError]}
          />
          {mismatch && <Text style={styles.errorText}>비밀번호가 일치하지 않아요</Text>}
        </View>

        {error && <Text style={styles.errorText}>{error}</Text>}
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  subtitle: { marginTop: 3 },
  label: { fontSize: 15, fontWeight: '500', color: C.navy, marginBottom: 10, paddingHorizontal: 2 },
  inputRow: { position: 'relative', justifyContent: 'center' },
  input: {
    backgroundColor: '#fff', borderRadius: 20,
    paddingVertical: 17, paddingHorizontal: 17, paddingRight: 48, fontSize: 16, color: C.navy,
    outlineWidth: 0,
  },
  inputPlain: { paddingRight: 17 },
  inputError: { borderWidth: 1.5, borderColor: '#dc2626' },
  eyeBtn: { position: 'absolute', right: 14, padding: 4 },
  errorText: { fontSize: 13, color: '#dc2626', marginTop: 6, paddingHorizontal: 2 },
  saveBtn: { borderRadius: 999, paddingVertical: 17, alignItems: 'center' },
});
