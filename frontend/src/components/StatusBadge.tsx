import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { RISK, RiskLevel } from '../theme/tokens';

export function StatusBadge({ risk }: { risk: RiskLevel }) {
  const r = RISK[risk];
  return (
    <View style={[styles.badge, { backgroundColor: r.ring }]}>
      <Text style={styles.text}>{r.label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: { paddingVertical: 2, paddingHorizontal: 8, borderRadius: 6, alignSelf: 'flex-end' },
  text: { color: '#fff', fontSize: 12, fontWeight: '500' },
});
