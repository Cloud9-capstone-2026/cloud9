import React from 'react';
import { Modal, View, Text, Pressable, StyleSheet } from 'react-native';
import { C, shadow, BIAS_LABELS, BIAS_COLORS } from '../theme/tokens';
import { BIAS_DESCS } from '../data/mock';
import { useAppState } from '../state/AppState';

export function BiasInfoModal() {
  const { biasInfo, closeBiasInfo } = useAppState();

  return (
    <Modal visible={biasInfo} transparent animationType="fade" onRequestClose={closeBiasInfo}>
      <View style={styles.overlay}>
        <View style={[styles.card, shadow.modal]}>
          <Text style={styles.title}>이 4가지 투자 편향이 뭔가요?</Text>
          <View style={{ gap: 20, marginTop: 18, marginBottom: 20 }}>
            {BIAS_LABELS.map((label, i) => (
              <View key={label} style={styles.row}>
                <View style={[styles.dot, { backgroundColor: BIAS_COLORS[i] }]} />
                <View style={{ flex: 1 }}>
                  <Text style={styles.name}>{label}</Text>
                  <Text style={styles.desc}>{BIAS_DESCS[i]}</Text>
                </View>
              </View>
            ))}
          </View>
          <Pressable onPress={closeBiasInfo} style={styles.confirmBtn}>
            <Text style={styles.confirmText}>확인</Text>
          </Pressable>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: { flex: 1, backgroundColor: 'rgba(16,24,40,0.42)', alignItems: 'center', justifyContent: 'center', paddingHorizontal: 32 },
  card: { width: '100%', backgroundColor: '#fff', borderRadius: 28, paddingTop: 26, paddingHorizontal: 22, paddingBottom: 18 },
  title: { fontSize: 18, fontWeight: '600', color: C.navy, textAlign: 'center' },
  row: { flexDirection: 'row', gap: 10 },
  dot: { width: 7, height: 7, borderRadius: 4, marginTop: 5 },
  name: { fontSize: 15, fontWeight: '600', color: C.navy, marginBottom: 2 },
  desc: { fontSize: 13, color: '#64748b', lineHeight: 19 },
  confirmBtn: { width: '100%', backgroundColor: C.blue, borderRadius: 999, paddingVertical: 17, alignItems: 'center' },
  confirmText: { fontSize: 16, fontWeight: '500', color: '#fff' },
});
