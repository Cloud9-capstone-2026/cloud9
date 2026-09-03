import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { C } from '../theme/tokens';
import { IconExt } from '../assets/icons';
import type { DartNews } from '../data/types';

export function NewsRow({ news, index, showCorp = true }: { news: DartNews; index: number; showCorp?: boolean }) {
  return (
    <View style={[styles.row, index > 0 && styles.divider]}>
      <View style={styles.metaRow}>
        <View style={styles.typeBadge}>
          <Text style={styles.typeText}>{news.type}</Text>
        </View>
        {showCorp && <Text style={styles.corp} numberOfLines={1}>{news.corp}</Text>}
        <View style={styles.metaSpacer} />
        <Text style={styles.date}>{news.date}</Text>
        <IconExt size={11} />
      </View>
      <Text style={styles.title} numberOfLines={2}>{news.title}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  row: { paddingVertical: 13 },
  divider: { borderTopWidth: 1, borderTopColor: C.border },
  metaRow: { flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 5 },
  metaSpacer: { flex: 1 },
  typeBadge: { backgroundColor: '#e8f0ff', borderRadius: 999, paddingVertical: 4, paddingHorizontal: 7, flexShrink: 0 },
  typeText: { fontSize: 11, fontWeight: '500', color: C.blue },
  corp: { fontSize: 12, fontWeight: '500', color: C.navy, flexShrink: 1, minWidth: 0 },
  date: { fontSize: 12, color: C.muted, flexShrink: 0 },
  title: { fontSize: 15, color: C.navy, lineHeight: 21, minHeight: 42 },
});
