import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useRoute } from '@react-navigation/native';
import { Screen } from '../components/Screen';
import { C } from '../theme/tokens';
import { LEGAL } from '../data/mock';

export function LegalScreen() {
  const route = useRoute<any>();
  const kind: 'terms' | 'privacy' = route.params?.kind || 'terms';
  const content = LEGAL[kind];

  return (
    <Screen back>
      <Text style={styles.title}>{content.title}</Text>
      <Text style={styles.meta}>{content.meta}</Text>
      <View style={styles.card}>
        {content.sections.map((s, i) => (
          <View key={s.h} style={[styles.section, i > 0 && styles.divider]}>
            <Text style={styles.h}>{s.h}</Text>
            <Text style={styles.p}>{s.p}</Text>
          </View>
        ))}
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  title: { fontSize: 22, fontWeight: '600', color: C.navy, letterSpacing: -0.3 },
  meta: { fontSize: 13, color: C.muted, marginTop: 4, marginBottom: 16 },
  card: { backgroundColor: '#fff', borderRadius: 30, paddingVertical: 20, paddingHorizontal: 18 },
  section: { paddingVertical: 14 },
  divider: { borderTopWidth: 1, borderTopColor: C.border },
  h: { fontSize: 16, fontWeight: '600', color: C.navy, marginBottom: 8 },
  p: { fontSize: 12.5, color: '#64748b', lineHeight: 22 },
});
