import React from 'react';
import { Modal, View, Text, Pressable, StyleSheet } from 'react-native';
import { C, shadow } from '../theme/tokens';

export function ConfirmModal({
  visible, title, body, confirmLabel, confirmColor = C.blue, cancelLabel = '취소',
  onConfirm, onCancel,
}: {
  visible: boolean;
  title: string;
  body: string;
  confirmLabel: string;
  confirmColor?: string;
  cancelLabel?: string;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return (
    <Modal visible={visible} transparent animationType="fade" onRequestClose={onCancel}>
      <View style={styles.overlay}>
        <View style={[styles.card, shadow.modal]}>
          <Text style={styles.title}>{title}</Text>
          <Text style={styles.body}>{body}</Text>
          <View style={styles.btnRow}>
            <Pressable onPress={onCancel} style={[styles.btn, styles.cancelBtn]}>
              <Text style={styles.cancelText}>{cancelLabel}</Text>
            </Pressable>
            <Pressable onPress={onConfirm} style={[styles.btn, { backgroundColor: confirmColor }]}>
              <Text style={styles.confirmText}>{confirmLabel}</Text>
            </Pressable>
          </View>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: { flex: 1, backgroundColor: 'rgba(16,24,40,0.42)', alignItems: 'center', justifyContent: 'center', paddingHorizontal: 32 },
  card: { width: '100%', backgroundColor: '#fff', borderRadius: 28, paddingTop: 26, paddingHorizontal: 22, paddingBottom: 18 },
  title: { fontSize: 19, fontWeight: '600', color: C.navy, textAlign: 'center' },
  body: { fontSize: 15, color: '#64748b', lineHeight: 22, textAlign: 'center', marginTop: 10, marginBottom: 20 },
  btnRow: { flexDirection: 'row', gap: 9 },
  btn: { flex: 1, borderRadius: 16, paddingVertical: 17, alignItems: 'center' },
  cancelBtn: { backgroundColor: '#f1f5f9' },
  cancelText: { fontSize: 16, fontWeight: '500', color: '#64748b' },
  confirmText: { fontSize: 16, fontWeight: '500', color: '#fff' },
});
