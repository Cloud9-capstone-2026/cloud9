import React, { useRef } from 'react';
import { View, ScrollView, StyleSheet, StyleProp, ViewStyle } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useScrollToTop, useFocusEffect } from '@react-navigation/native';
import { C } from '../theme/tokens';
import { Header } from './Header';
import { TAB_BAR_CLEARANCE } from '../navigation/BottomTabBar';

export function Screen({
  back,
  contentStyle,
  footer,
  // 이 화면이 하단 탭 화면(TabNavigator) 안에서 쓰여서 둥둥 뜬 탭바가 겹치는 경우 true —
  // footer(페이지네이션)가 탭바에 가리지 않도록 그만큼 여유 공간을 더 줌.
  belowTabBar,
  children,
}: {
  back?: boolean;
  contentStyle?: StyleProp<ViewStyle>;
  footer?: React.ReactNode;
  belowTabBar?: boolean;
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
        contentContainerStyle={[styles.content, !!footer && styles.contentWithFooter, contentStyle]}
      >
        {children}
        {footer && (
          <View
            style={[
              styles.footer,
              { paddingBottom: (belowTabBar ? TAB_BAR_CLEARANCE : 0) + Math.max(16, insets.bottom) + 8 },
            ]}
          >
            {footer}
          </View>
        )}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: C.bg },
  content: { paddingHorizontal: 22, paddingTop: 4, paddingBottom: 110 },
  // footer(페이지네이션)가 있는 화면은 콘텐츠가 짧아도 화면 하단에 붙고,
  // 콘텐츠가 길어서 스크롤이 생기면 그 콘텐츠 맨 아래에 자연스럽게 따라오도록
  // flexGrow + marginTop:'auto' 조합으로 "하단 고정"을 스크롤 영역 안에서 구현.
  contentWithFooter: { flexGrow: 1, paddingBottom: 0 },
  footer: { marginTop: 'auto', paddingTop: 16, marginHorizontal: -22, paddingHorizontal: 22, backgroundColor: C.bg },
});
