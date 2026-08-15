import React from 'react';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import type { TabParamList } from './types';
import { BottomTabBar } from './BottomTabBar';
import { HomeScreen } from '../screens/HomeScreen';
import { ReportListScreen } from '../screens/ReportListScreen';
import { JournalListScreen } from '../screens/JournalListScreen';
import { MyPageScreen } from '../screens/MyPageScreen';
import { SettingsScreen } from '../screens/SettingsScreen';

const Tab = createBottomTabNavigator<TabParamList>();

export function TabNavigator() {
  return (
    <Tab.Navigator
      screenOptions={{ headerShown: false }}
      tabBar={(props) => <BottomTabBar {...props} />}
    >
      <Tab.Screen name="Home" component={HomeScreen} />
      <Tab.Screen name="ReportList" component={ReportListScreen} />
      <Tab.Screen name="JournalList" component={JournalListScreen} />
      <Tab.Screen name="MyPage" component={MyPageScreen} />
      <Tab.Screen name="Settings" component={SettingsScreen} />
    </Tab.Navigator>
  );
}
