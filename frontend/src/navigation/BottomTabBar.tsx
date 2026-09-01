import React from 'react';
import { View, Text, Pressable, StyleSheet } from 'react-native';
import type { BottomTabBarProps } from '@react-navigation/bottom-tabs';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { C, shadow } from '../theme/tokens';
import { IconHome, IconChart, IconBook, IconRadar, IconGear } from '../assets/icons';

const ICONS: Record<string, (active: boolean) => React.ReactNode> = {
  Home: (a) => <IconHome active={a} />,
  ReportList: (a) => <IconChart active={a} />,
  JournalList: (a) => <IconBook active={a} />,
  MyPage: (a) => <IconRadar active={a} />,
  Settings: (a) => <IconGear active={a} />,
};

const LABELS: Record<string, string> = {
  Home: '홈',
  ReportList: '리포트',
  JournalList: '거래일지',
  MyPage: '성향분석',
  Settings: '설정',
};

export function BottomTabBar({ state, navigation }: BottomTabBarProps) {
  const insets = useSafeAreaInsets();
  return (
    <View style={[styles.wrap, { bottom: Math.max(16, insets.bottom) }]}>
      <View style={[styles.bar, shadow.floating]}>
        {state.routes.map((route, i) => {
          const active = state.index === i;
          const iconRenderer = ICONS[route.name];
          return (
            <Pressable
              key={route.key}
              onPress={() => {
                const event = navigation.emit({ type: 'tabPress', target: route.key, canPreventDefault: true });
                if (!active && !event.defaultPrevented) navigation.navigate(route.name);
              }}
              style={[styles.tab, { backgroundColor: active ? C.mutedBg : 'transparent' }]}
            >
              {iconRenderer?.(active)}
              <Text style={[styles.label, { color: active ? C.blue : C.muted, fontWeight: active ? '600' : '400' }]}>
                {LABELS[route.name]}
              </Text>
            </Pressable>
          );
        })}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    position: 'absolute', left: 0, right: 0, alignItems: 'center',
  },
  bar: {
    backgroundColor: C.card,
    borderRadius: 999,
    paddingVertical: 8,
    paddingHorizontal: 12,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 2,
    width: '100%',
    maxWidth: 370,
    marginHorizontal: 16,
  },
  tab: {
    flex: 1,
    alignItems: 'center',
    gap: 3,
    borderRadius: 999,
    paddingVertical: 7,
    paddingHorizontal: 4,
  },
  label: { fontSize: 11, letterSpacing: -0.1 },
});
