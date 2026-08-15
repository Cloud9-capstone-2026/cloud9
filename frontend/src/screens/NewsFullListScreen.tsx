import React from 'react';
import { Text, StyleSheet } from 'react-native';
import { Screen } from '../components/Screen';
import { Card } from '../components/Card';
import { NewsRow } from '../components/NewsRow';
import { C } from '../theme/tokens';
import { dartNews } from '../data/mock';

export function NewsFullListScreen() {
  return (
    <Screen back>
      <Text style={styles.title}>전체 소식</Text>
      <Card>
        {dartNews.map((n, i) => (
          <NewsRow key={n.id} news={n} index={i} />
        ))}
      </Card>
    </Screen>
  );
}

const styles = StyleSheet.create({
  title: { fontSize: 20, fontWeight: '600', color: C.navy, letterSpacing: -0.3, marginBottom: 18 },
});
