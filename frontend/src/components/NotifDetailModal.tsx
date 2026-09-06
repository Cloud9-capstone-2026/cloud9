import React from 'react';
import { Modal, View, Text, Pressable, StyleSheet } from 'react-native';
import { C, shadow } from '../theme/tokens';

export function NotifDetailModal({
  visible, iconBg, icon, title, body, time, onClose,
}: {
  visible: boolean;
  iconBg: string;
  icon: React.ReactNode;
  title: string;
  body: string;
  time: string;
  onClose: () => void;
}) {
  return (
    <Modal visible={visible} transparent animationType="fade" onRequestClose={onClose}>
      <View style={styles.overlay}>
        <View style={[styles.card, shadow.modal]}>
          <View style={[styles.iconBox, { backgroundColor: iconBg }]}>{icon}</View>
          <Text style={styles.title}>{title}</Text>
          <Text style={styles.body}>{body}</Text>
          <Text style={styles.time}>{time}</Text>
          <Pressable onPress={onClose} style={styles.confirmBtn}>
            <Text style={styles.confirmText}>확인</Text>
          </Pressable>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: { flex: 1, backgroundColor: 'rgba(16,24,40,0.42)', alignItems: 'center', justifyContent: 'center', paddingHorizontal: 32 },
  card: { width: '100%', backgroundColor: '#fff', borderRadius: 28, paddingTop: 26, paddingHorizontal: 22, paddingBottom: 18, alignItems: 'center' },
  iconBox: { width: 46, height: 46, borderRadius: 16, alignItems: 'center', justifyContent: 'center', marginBottom: 14 },
  title: { fontSize: 18, fontWeight: '600', color: C.navy, textAlign: 'center' },
  body: { fontSize: 15, color: '#64748b', lineHeight: 22, textAlign: 'center', marginTop: 10 },
  time: { fontSize: 12, color: '#cbd5e1', marginTop: 8, marginBottom: 18 },
  confirmBtn: { width: '100%', backgroundColor: C.blue, borderRadius: 999, paddingVertical: 17, alignItems: 'center' },
  confirmText: { fontSize: 16, fontWeight: '500', color: '#fff' },
});
