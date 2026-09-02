import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { C } from '../theme/tokens';

export function EmptyState({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <View style={styles.root}>
      <Text style={styles.title}>{title}</Text>
      {subtitle && <Text style={styles.subtitle}>{subtitle}</Text>}
    </View>
  );
}

const styles = StyleSheet.create({
  root: { alignItems: 'center', justifyContent: 'center', paddingVertical: 40, gap: 6 },
  title: { fontSize: 15, color: C.muted, fontWeight: '500' },
  subtitle: { fontSize: 13, color: C.muted, textAlign: 'center', lineHeight: 19 },
});
