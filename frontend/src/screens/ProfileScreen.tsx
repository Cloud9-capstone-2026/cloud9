import React, { useState } from 'react';
import { View, Text, TextInput, Pressable, ScrollView, StyleSheet } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { LinearGradient } from 'expo-linear-gradient';
import { Header } from '../components/Header';
import { ConfirmModal } from '../components/ConfirmModal';
import { C } from '../theme/tokens';
import { useAppState } from '../state/AppState';
import type { RootStackParamList } from '../navigation/types';

export function ProfileScreen() {
  const navigation = useNavigation<NativeStackNavigationProp<RootStackParamList>>();
  const insets = useSafeAreaInsets();
  const { pfName, setPfName, logout } = useAppState();
  const [name, setName] = useState(pfName);
  const [withdrawOpen, setWithdrawOpen] = useState(false);
  const canSave = name.trim().length > 0;

  return (
    <View style={styles.root}>
      <Header back />
      <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
        <Text style={styles.title}>프로필 수정</Text>

        <View style={styles.avatarWrap}>
          <LinearGradient colors={['#2563eb', '#60a5fa']} start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }} style={styles.avatar}>
            <Text style={styles.avatarInitial}>{(name || '김')[0]}</Text>
          </LinearGradient>
          <Text style={styles.changePhoto}>사진 변경</Text>
        </View>

        <View style={{ gap: 14 }}>
          <View>
            <Text style={styles.label}>닉네임</Text>
            <TextInput value={name} onChangeText={setName} style={styles.input} placeholderTextColor={C.muted} />
          </View>
          <View>
            <Text style={styles.label}>이메일</Text>
            <View style={[styles.input, styles.readonly]}>
              <Text style={styles.readonlyText}>kim.invest@email.com</Text>
            </View>
            <Text style={styles.readonlyNote}>이메일은 변경할 수 없어요</Text>
          </View>
          <View>
            <Text style={styles.label}>비밀번호</Text>
            <Pressable
              onPress={() => navigation.navigate('ProfileVerify', { mode: 'changePw' })}
              style={styles.pwRow}
            >
              <Text style={styles.pwLabel}>비밀번호 변경</Text>
              <Text style={styles.pwArrow}>›</Text>
            </Pressable>
          </View>
        </View>

        <Pressable onPress={() => setWithdrawOpen(true)} style={{ marginTop: 30, alignItems: 'center' }}>
          <Text style={styles.withdraw}>회원 탈퇴</Text>
        </Pressable>
      </ScrollView>

      <View style={[styles.footer, { paddingBottom: Math.max(16, insets.bottom) + 8 }]}>
        <Pressable
          onPress={() => { setPfName(name); navigation.goBack(); }}
          disabled={!canSave}
          style={[styles.saveBtn, { backgroundColor: canSave ? C.blue : '#e2e8f0' }]}
        >
          <Text style={{ color: canSave ? '#fff' : '#a5b4c8', fontSize: 17, fontWeight: '600' }}>저장하기</Text>
        </Pressable>
      </View>

      <ConfirmModal
        visible={withdrawOpen}
        title="정말 탈퇴할까요?"
        body={'업로드한 거래 내역, 분석 리포트,\n거래일지가 모두 삭제되며 복구할 수 없어요.'}
        confirmLabel="탈퇴하기"
        confirmColor="#dc2626"
        onConfirm={() => { setWithdrawOpen(false); logout(); }}
        onCancel={() => setWithdrawOpen(false)}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  content: { paddingHorizontal: 22, paddingTop: 4, paddingBottom: 120 },
  title: { fontSize: 22, fontWeight: '600', color: C.navy, letterSpacing: -0.3, marginBottom: 20 },
  avatarWrap: { alignItems: 'center', gap: 8, marginBottom: 26 },
  avatar: { width: 76, height: 76, borderRadius: 38, alignItems: 'center', justifyContent: 'center' },
  avatarInitial: { fontSize: 30, fontWeight: '600', color: '#fff' },
  changePhoto: { fontSize: 13, fontWeight: '500', color: C.blue },
  label: { fontSize: 15, fontWeight: '500', color: C.navy, marginBottom: 10, paddingHorizontal: 2 },
  input: {
    backgroundColor: '#fff', borderRadius: 20,
    paddingVertical: 17, paddingHorizontal: 17, fontSize: 16, color: C.navy,
  },
  readonly: { backgroundColor: '#f1f5f9' },
  readonlyText: { fontSize: 16, color: C.muted },
  readonlyNote: { fontSize: 12, color: '#cbd5e1', marginTop: 6, paddingHorizontal: 2 },
  pwRow: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    backgroundColor: '#fff', borderRadius: 20, paddingVertical: 15, paddingHorizontal: 17,
  },
  pwLabel: { fontSize: 16, color: C.navy },
  pwArrow: { fontSize: 20, color: C.muted },
  withdraw: { fontSize: 15, color: '#dc2626', textDecorationLine: 'underline' },
  footer: { position: 'absolute', left: 22, right: 22, bottom: 0 },
  saveBtn: { borderRadius: 999, paddingVertical: 17, alignItems: 'center' },
});
