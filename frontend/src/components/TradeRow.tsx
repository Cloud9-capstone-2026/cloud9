import React from 'react';
import { View, Text, Pressable, StyleSheet } from 'react-native';
import { C, riskLevel } from '../theme/tokens';
import { StatusBadge } from './StatusBadge';
import type { Trade } from '../data/types';

export function TradeRow({ trade, index, onPress }: { trade: Trade; index: number; onPress: () => void }) {
  const risk = riskLevel(trade.score);
  const isBuy = trade.type === 'buy';
  return (
    <Pressable
      onPress={onPress}
      style={[styles.row, index > 0 && styles.divider]}
    >
      <View>
        <Text style={styles.stock}>{trade.stock}</Text>
        <View style={styles.metaRow}>
          <Text style={styles.date}>{trade.date}</Text>
          <Text style={[styles.type, { color: isBuy ? C.red : C.blue }]}>{isBuy ? '매수' : '매도'}</Text>
        </View>
      </View>
      <View style={styles.right}>
        <Text style={styles.amount}>{trade.amount}원</Text>
        <StatusBadge risk={risk} />
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingVertical: 13 },
  divider: { borderTopWidth: 1, borderTopColor: C.border },
  stock: { fontSize: 15, fontWeight: '500', color: C.navy, marginBottom: 4, letterSpacing: -0.1 },
  metaRow: { flexDirection: 'row', alignItems: 'center', gap: 7 },
  date: { fontSize: 12, color: C.muted },
  type: { fontSize: 12, fontWeight: '500' },
  right: { alignItems: 'flex-end' },
  amount: { fontSize: 14, fontWeight: '500', color: C.navy, marginBottom: 5 },
});
