import React from 'react';
import { View, StyleSheet, StyleProp, ViewStyle } from 'react-native';
import { C } from '../theme/tokens';

// 카드 기본 padding — 빈 상태에서 카드 크기를 유지해야 할 때 이 값으로 계산해서 재사용할 것.
export const CARD_PADDING = 16;

export function Card({ style, children }: { style?: StyleProp<ViewStyle>; children: React.ReactNode }) {
  return <View style={[styles.card, style]}>{children}</View>;
}

const styles = StyleSheet.create({
  card: { backgroundColor: C.card, borderRadius: 30, padding: CARD_PADDING },
});
