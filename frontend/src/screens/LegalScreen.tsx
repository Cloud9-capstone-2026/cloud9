import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { useRoute } from '@react-navigation/native';
import { AuthScreen } from '../components/AuthScreen';
import { HeaderActions } from '../components/Header';
import { C } from '../theme/tokens';
import { LEGAL } from '../data/mock';

export function LegalScreen() {
  const route = useRoute<any>();
  const kind: 'terms' | 'privacy' = route.params?.kind || 'terms';
  const variant: 'auth' | 'app' = route.params?.variant || 'app';
  const content = LEGAL[kind];

  return (
    <AuthScreen back headerRight={variant === 'app' ? <HeaderActions /> : undefined}>
      <Text style={styles.title}>{content.title}</Text>
      <View style={styles.card}>
        {content.sections.map((s, i) => (
          <View key={s.h} style={[styles.section, i > 0 && styles.divider]}>
            <Text style={styles.h}>{s.h}</Text>
            <Text style={styles.p}>{s.p}</Text>
          </View>
        ))}
      </View>
    </AuthScreen>
  );
}

const styles = StyleSheet.create({
  title: { fontSize: 22, fontWeight: '600', color: C.navy, letterSpacing: -0.3 },
  card: { backgroundColor: '#fff', borderRadius: 30, paddingVertical: 20, paddingHorizontal: 18, marginTop: 16 },
  section: { paddingVertical: 14 },
  divider: { borderTopWidth: 1, borderTopColor: C.border },
  h: { fontSize: 16, fontWeight: '600', color: C.navy, marginBottom: 8 },
  p: { fontSize: 12.5, color: '#64748b', lineHeight: 22 },
});
