import React from 'react';
import { View, StyleSheet, StyleProp, ViewStyle } from 'react-native';
import { C } from '../theme/tokens';

export function Card({ style, children }: { style?: StyleProp<ViewStyle>; children: React.ReactNode }) {
  return <View style={[styles.card, style]}>{children}</View>;
}

const styles = StyleSheet.create({
  card: { backgroundColor: C.card, borderRadius: 30, padding: 16 },
});
