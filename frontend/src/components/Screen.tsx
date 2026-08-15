import React from 'react';
import { View, ScrollView, StyleSheet, StyleProp, ViewStyle } from 'react-native';
import { C } from '../theme/tokens';
import { Header } from './Header';

export function Screen({
  back,
  contentStyle,
  children,
}: {
  back?: boolean;
  contentStyle?: StyleProp<ViewStyle>;
  children: React.ReactNode;
}) {
  return (
    <View style={styles.root}>
      <Header back={back} />
      <ScrollView
        showsVerticalScrollIndicator={false}
        contentContainerStyle={[styles.content, contentStyle]}
      >
        {children}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  content: { paddingHorizontal: 22, paddingTop: 4, paddingBottom: 110 },
});
