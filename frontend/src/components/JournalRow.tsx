import React from 'react';
import { View, Text, Pressable, StyleSheet } from 'react-native';
import { C } from '../theme/tokens';
import { StatusBadge } from './StatusBadge';
import type { Journal } from '../data/types';

export function JournalRow({ journal, index, onPress }: { journal: Journal; index: number; onPress: () => void }) {
  const isBuy = journal.type === 'buy';
  return (
    <Pressable onPress={onPress} style={[styles.row, index > 0 && styles.divider]}>
      <View style={styles.left}>
        <Text style={styles.stock} numberOfLines={1}>{journal.stock}</Text>
        <View style={styles.metaRow}>
          <Text style={styles.date}>{journal.date}</Text>
          <Text style={[styles.type, { color: isBuy ? C.red : C.blue }]}>{isBuy ? '매수' : '매도'}</Text>
        </View>
      </View>
      <View style={styles.right}>
        <Text style={styles.emotion}>#{journal.emotion}</Text>
        <StatusBadge risk={journal.risk} />
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingVertical: 13 },
  divider: { borderTopWidth: 1, borderTopColor: C.border },
  left: { flex: 1, minWidth: 0, paddingRight: 12 },
  stock: { fontSize: 18, fontWeight: '600', color: C.navy, marginBottom: 4, letterSpacing: -0.1 },
  metaRow: { flexDirection: 'row', alignItems: 'center', gap: 7 },
  date: { fontSize: 13, color: C.muted },
  type: { fontSize: 13, fontWeight: '500' },
  right: { alignItems: 'flex-end', flexShrink: 0 },
  emotion: { fontSize: 15, fontWeight: '600', color: C.navy, marginBottom: 5 },
});
