import React, { useRef } from 'react';
import { View, ScrollView, StyleSheet, StyleProp, ViewStyle } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useScrollToTop, useFocusEffect } from '@react-navigation/native';
import { C } from '../theme/tokens';
import { Header } from './Header';

export function Screen({
  back,
  contentStyle,
  footer,
  children,
}: {
  back?: boolean;
  contentStyle?: StyleProp<ViewStyle>;
  footer?: React.ReactNode;
  children: React.ReactNode;
}) {
  const insets = useSafeAreaInsets();
  const scrollRef = useRef<ScrollView>(null);

  useScrollToTop(scrollRef);
  useFocusEffect(
    React.useCallback(() => {
      scrollRef.current?.scrollTo({ y: 0, animated: false });
    }, [])
  );

  return (
    <View style={styles.root}>
      <Header back={back} />
      <ScrollView
        ref={scrollRef}
        showsVerticalScrollIndicator={false}
        contentContainerStyle={[styles.content, !!footer && { paddingBottom: 150 }, contentStyle]}
      >
        {children}
      </ScrollView>
      {footer && (
        <View style={[styles.footer, { paddingBottom: Math.max(16, insets.bottom) + 8 }]}>
          {footer}
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  content: { paddingHorizontal: 22, paddingTop: 4, paddingBottom: 110 },
  footer: { position: 'absolute', left: 0, right: 0, bottom: 0, paddingHorizontal: 22, backgroundColor: C.bg },
});
