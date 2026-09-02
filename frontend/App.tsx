import React from 'react';
import { View, StyleSheet } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { NavigationContainer } from '@react-navigation/native';
import { AppStateProvider, useAppState } from './src/state/AppState';
import { RootNavigator } from './src/navigation/RootNavigator';
import { AuthNavigator } from './src/navigation/AuthNavigator';
import { OnboardingNavigator } from './src/navigation/OnboardingNavigator';
import { navigationRef } from './src/navigation/navigationRef';
import { C } from './src/theme/tokens';

function AppSwitch() {
  const { authPhase, authReady } = useAppState();
  // 로그인 상태 유지 여부를 로컬 저장소에서 확인하는 동안 빈 화면(같은 배경색)을 잠깐 보여줘서
  // "저장된 세션이 있는데도 로그인 화면이 잠깐 보였다가 사라지는" 깜빡임을 방지.
  if (!authReady) return <View style={styles.phone} />;
  if (authPhase === 'auth') return <AuthNavigator />;
  if (authPhase === 'onboarding') return <OnboardingNavigator />;
  return <RootNavigator />;
}

export default function App() {
  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <SafeAreaProvider>
        <View style={styles.outer}>
          <View style={styles.phone}>
            <AppStateProvider>
              <NavigationContainer ref={navigationRef}>
                <AppSwitch />
              </NavigationContainer>
            </AppStateProvider>
          </View>
        </View>
        <StatusBar style="dark" />
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}

const styles = StyleSheet.create({
  outer: { flex: 1, backgroundColor: '#dde3ee', alignItems: 'center' },
  phone: { flex: 1, width: '100%', maxWidth: 430, backgroundColor: C.bg },
});
