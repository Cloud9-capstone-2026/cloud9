import React from 'react';
import { View, Text, Pressable, StyleSheet } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Screen } from '../components/Screen';
import { Card } from '../components/Card';
import { IconArrow } from '../assets/icons';
import { C } from '../theme/tokens';
import { useAppState } from '../state/AppState';

function ToggleRow({ label, sub, value, onToggle, divider }: {
  label: string; sub: string; value: boolean; onToggle: () => void; divider?: boolean;
}) {
  return (
    <View style={[styles.toggleRow, divider && styles.divider]}>
      <View>
        <Text style={styles.toggleLabel}>{label}</Text>
        <Text style={styles.toggleSub}>{sub}</Text>
      </View>
      <Pressable onPress={onToggle} style={[styles.switchTrack, { backgroundColor: value ? C.blue : C.border }]}>
        <View style={[styles.switchKnob, { left: value ? 21 : 3 }]} />
      </Pressable>
    </View>
  );
}

function AccountRow({ label, color, divider }: { label: string; color?: string; divider?: boolean }) {
  return (
    <View style={[styles.accountRow, divider && styles.divider]}>
      <Text style={[styles.accountLabel, color ? { color } : null]}>{label}</Text>
      <IconArrow size={13} />
    </View>
  );
}

export function SettingsScreen() {
  const { notif, auto, toggleNotif, toggleAuto } = useAppState();

  return (
    <Screen contentStyle={styles.content}>
      <Text style={styles.title}>설정</Text>

      <Card style={styles.profileCard}>
        <LinearGradient colors={['#2563eb', '#60a5fa']} start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }} style={styles.avatarCircle}>
          <Text style={styles.avatarInitial}>김</Text>
        </LinearGradient>
        <View style={{ flex: 1 }}>
          <Text style={styles.profileName}>김투자</Text>
          <Text style={styles.profileEmail}>kim.invest@email.com</Text>
          <View style={{ marginTop: 8, alignItems: 'flex-end' }}>
            <Text style={styles.editProfile}>프로필 수정 →</Text>
          </View>
        </View>
      </Card>

      <Card>
        <Text style={styles.sectionLabel}>알림 설정</Text>
        <ToggleRow label="이상 탐지 알림" sub="위험 거래 감지 시 즉시 알림" value={notif} onToggle={toggleNotif} />
        <ToggleRow label="자동 분석" sub="업로드 후 자동으로 분석 시작" value={auto} onToggle={toggleAuto} divider />
      </Card>

      <Card>
        <Text style={styles.sectionLabel}>계정</Text>
        <AccountRow label="개인정보 처리방침" />
        <AccountRow label="이용약관" divider />
        <AccountRow label="로그아웃" color={C.red} divider />
      </Card>

      <Text style={styles.footer}>Canary v1.2.0 · © 2026 Canary Analytics</Text>
    </Screen>
  );
}

const styles = StyleSheet.create({
  content: { gap: 18 },
  title: { fontSize: 20, fontWeight: '600', color: C.navy, letterSpacing: -0.3 },
  profileCard: { flexDirection: 'row', alignItems: 'center', gap: 14 },
  avatarCircle: {
    width: 52, height: 52, borderRadius: 26,
    alignItems: 'center', justifyContent: 'center',
  },
  avatarInitial: { fontSize: 19, color: '#fff', fontWeight: '600' },
  profileName: { fontSize: 16, fontWeight: '600', color: C.navy, lineHeight: 22 },
  profileEmail: { fontSize: 12, color: C.muted, marginTop: 2 },
  editProfile: { fontSize: 12, fontWeight: '500', color: C.blue },
  sectionLabel: { fontSize: 11, fontWeight: '500', color: C.muted, letterSpacing: 0.5, marginBottom: 10 },
  toggleRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingVertical: 13 },
  divider: { borderTopWidth: 1, borderTopColor: C.border },
  toggleLabel: { fontSize: 14, color: C.navy, lineHeight: 21 },
  toggleSub: { fontSize: 11, color: C.muted, marginTop: 2, lineHeight: 17 },
  switchTrack: { width: 44, height: 26, borderRadius: 999, justifyContent: 'center' },
  switchKnob: {
    position: 'absolute', width: 20, height: 20, borderRadius: 10, backgroundColor: '#fff',
    shadowColor: '#000', shadowOpacity: 0.18, shadowRadius: 3, shadowOffset: { width: 0, height: 1 }, elevation: 2,
  },
  accountRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingVertical: 13 },
  accountLabel: { fontSize: 14, color: C.navy, lineHeight: 21 },
  footer: { textAlign: 'center', fontSize: 11, color: C.muted, paddingVertical: 6 },
});
