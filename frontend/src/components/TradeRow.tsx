import React from 'react';
import { View, Text, Pressable, StyleSheet } from 'react-native';
import { C, riskLevel } from '../theme/tokens';
import { StatusBadge } from './StatusBadge';
import type { Trade } from '../data/types';

// 실측 렌더 높이(paddingVertical 13*2 + 종목명/날짜 두 줄, StatusBadge 포함) — 이 로우를 쓰는
// 카드가 빈 상태일 때 카드 크기를 유지해야 하면 새로 높이를 재지 말고 이 값 * 행 수로 재사용할 것.
// (로우 안의 폰트 크기나 뱃지 패딩을 바꾸면 이 값도 다시 재서 갱신해야 함.)
export const TRADE_ROW_HEIGHT = 72.8;

export function TradeRow({ trade, index, onPress }: { trade: Trade; index: number; onPress: () => void }) {
  const risk = riskLevel(trade.score);
  const isBuy = trade.type === 'buy';
  return (
    <Pressable
      onPress={onPress}
      style={[styles.row, index > 0 && styles.divider]}
    >
      <View style={styles.left}>
        <Text style={styles.stock} numberOfLines={1}>{trade.stock}</Text>
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
  left: { flex: 1, minWidth: 0, paddingRight: 12 },
  stock: { fontSize: 17, fontWeight: '600', color: C.navy, marginBottom: 4, letterSpacing: -0.1 },
  metaRow: { flexDirection: 'row', alignItems: 'center', gap: 7 },
  date: { fontSize: 13, color: C.muted },
  type: { fontSize: 13, fontWeight: '500' },
  right: { alignItems: 'flex-end', flexShrink: 0 },
  amount: { fontSize: 16, fontWeight: '500', color: C.navy, marginBottom: 5 },
});
