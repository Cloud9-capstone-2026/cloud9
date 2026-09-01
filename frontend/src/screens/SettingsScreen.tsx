import React, { useState } from 'react';
import { View, Text, Pressable, StyleSheet } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Screen } from '../components/Screen';
import { Card } from '../components/Card';
import { ConfirmModal } from '../components/ConfirmModal';
import { IconArrow } from '../assets/icons';
import { C } from '../theme/tokens';
import { useAppState } from '../state/AppState';
import { goToProfile, goToLegal, goToRulesSettings } from '../navigation/navigationRef';

function AccountRow({ label, color, divider, onPress }: { label: string; color?: string; divider?: boolean; onPress?: () => void }) {
  return (
    <Pressable onPress={onPress} style={[styles.accountRow, divider && styles.divider]}>
      <Text style={[styles.accountLabel, color ? { color } : null]}>{label}</Text>
      <IconArrow size={13} />
    </Pressable>
  );
}

export function SettingsScreen() {
  const { notif, toggleNotif, osNotif, pfName, logout } = useAppState();
  const [logoutOpen, setLogoutOpen] = useState(false);
  const notifLocked = osNotif === 'denied';

  return (
    <Screen contentStyle={styles.content}>
      <Text style={styles.title}>설정</Text>

      <Card style={styles.profileCard}>
        <LinearGradient colors={['#2563eb', '#60a5fa']} start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }} style={styles.avatarCircle}>
          <Text style={styles.avatarInitial}>{(pfName || '김')[0]}</Text>
        </LinearGradient>
        <View style={{ flex: 1 }}>
          <Text style={styles.profileName}>{pfName}</Text>
          <Text style={styles.profileEmail}>kim.invest@email.com</Text>
          <Pressable onPress={goToProfile} style={{ marginTop: 8, alignItems: 'flex-end' }}>
            <Text style={styles.editProfile}>프로필 수정 →</Text>
          </Pressable>
        </View>
      </Card>

      <View>
        <Text style={styles.sectionLabel}>알림 설정</Text>
        <Card>
          <View style={styles.toggleRow}>
            <View style={{ flex: 1, paddingRight: 12 }}>
              <Text style={[styles.toggleLabel, notifLocked && { color: '#94a3b8' }]}>알림 받기</Text>
              <Text style={styles.toggleSub}>
                {notifLocked ? '기기 설정에서 알림 설정을 허용해주세요' : '업로드와 분석이 끝나면 알려드려요'}
              </Text>
            </View>
            <Pressable
              onPress={notifLocked ? undefined : toggleNotif}
              style={[
                styles.switchTrack,
                { backgroundColor: notif && !notifLocked ? C.blue : C.border },
                notifLocked && { opacity: 0.45 },
              ]}
            >
              <View style={[styles.switchKnob, { left: notif && !notifLocked ? 21 : 3 }]} />
            </Pressable>
          </View>
        </Card>
      </View>

      <View>
        <Text style={styles.sectionLabel}>분석 설정</Text>
        <Card>
          <Pressable onPress={goToRulesSettings} style={styles.toggleRow}>
            <View style={{ flex: 1, paddingRight: 12 }}>
              <Text style={styles.toggleLabel}>탐지 규칙 설정</Text>
              <Text style={styles.toggleSub}>규칙 계층의 판정 기준을 직접 설정할 수 있어요</Text>
            </View>
            <IconArrow size={13} />
          </Pressable>
        </Card>
      </View>

      <View>
        <Text style={styles.sectionLabel}>계정</Text>
        <Card>
          <AccountRow label="개인정보 처리방침" onPress={() => goToLegal('privacy')} />
          <AccountRow label="이용약관" divider onPress={() => goToLegal('terms')} />
          <AccountRow label="로그아웃" color={C.red} divider onPress={() => setLogoutOpen(true)} />
        </Card>
      </View>

      <Text style={styles.footer}>Canary v1.2.0 · © 2026 Canary Analytics</Text>

      <ConfirmModal
        visible={logoutOpen}
        title="로그아웃할까요?"
        body="다시 이용하려면 로그인이 필요해요."
        confirmLabel="로그아웃"
        confirmColor="#dc2626"
        onConfirm={() => { setLogoutOpen(false); logout(); }}
        onCancel={() => setLogoutOpen(false)}
      />
    </Screen>
  );
}

const styles = StyleSheet.create({
  content: { gap: 22 },
  title: { fontSize: 22, fontWeight: '600', color: C.navy, letterSpacing: -0.3 },
  profileCard: { flexDirection: 'row', alignItems: 'center', gap: 14 },
  avatarCircle: {
    width: 52, height: 52, borderRadius: 26,
    alignItems: 'center', justifyContent: 'center',
  },
  avatarInitial: { fontSize: 21, color: '#fff', fontWeight: '600' },
  profileName: { fontSize: 18, fontWeight: '600', color: C.navy, lineHeight: 22 },
  profileEmail: { fontSize: 13, color: C.muted, marginTop: 2 },
  editProfile: { fontSize: 13, fontWeight: '500', color: C.blue },
  sectionLabel: { fontSize: 15, fontWeight: '500', color: '#64748b', marginBottom: 9, paddingLeft: 6 },
  toggleRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingVertical: 4 },
  divider: { borderTopWidth: 1, borderTopColor: C.border },
  toggleLabel: { fontSize: 16, color: C.navy, lineHeight: 21 },
  toggleSub: { fontSize: 12, color: C.muted, marginTop: 2, lineHeight: 17 },
  switchTrack: { width: 44, height: 26, borderRadius: 999, justifyContent: 'center' },
  switchKnob: {
    position: 'absolute', width: 20, height: 20, borderRadius: 10, backgroundColor: '#fff',
    shadowColor: '#000', shadowOpacity: 0.18, shadowRadius: 3, shadowOffset: { width: 0, height: 1 }, elevation: 2,
  },
  accountRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingVertical: 13 },
  accountLabel: { fontSize: 16, color: C.navy, lineHeight: 21 },
  footer: { textAlign: 'center', fontSize: 12, color: C.muted, paddingVertical: 6 },
});
