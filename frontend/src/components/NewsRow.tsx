import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { C } from '../theme/tokens';
import { IconExt } from '../assets/icons';
import type { DartNews } from '../data/types';

export function NewsRow({ news, index, showCorp = true }: { news: DartNews; index: number; showCorp?: boolean }) {
  return (
    <View style={[styles.row, index > 0 && styles.divider]}>
      <View style={styles.content}>
        <View style={styles.metaRow}>
          <View style={styles.typeBadge}>
            <Text style={styles.typeText}>{news.type}</Text>
          </View>
          {showCorp && <Text style={styles.corp}>{news.corp}</Text>}
          <Text style={styles.date}>{news.date}</Text>
        </View>
        <Text style={styles.title}>{news.title}</Text>
      </View>
      <View style={{ marginTop: 2 }}>
        <IconExt size={11} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'flex-start', gap: 10, paddingVertical: 13 },
  divider: { borderTopWidth: 1, borderTopColor: C.border },
  content: { flex: 1 },
  metaRow: { flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 5, flexWrap: 'wrap' },
  typeBadge: { backgroundColor: '#e8f0ff', borderRadius: 999, paddingVertical: 2, paddingHorizontal: 7 },
  typeText: { fontSize: 10, fontWeight: '500', color: C.blue },
  corp: { fontSize: 11, fontWeight: '500', color: C.navy },
  date: { fontSize: 11, color: C.muted },
  title: { fontSize: 13, color: C.navy, lineHeight: 21 },
});
