import React from 'react';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import type { OnboardingStackParamList } from './types';
import { TutorialScreen } from '../screens/TutorialScreen';
import { TutRulesEditScreen } from '../screens/TutRulesEditScreen';
import { DiagnosisScreen } from '../screens/DiagnosisScreen';

const Stack = createNativeStackNavigator<OnboardingStackParamList>();

export function OnboardingNavigator() {
  return (
    <Stack.Navigator screenOptions={{ headerShown: false, gestureEnabled: false }}>
      <Stack.Screen name="Tutorial" component={TutorialScreen} />
      <Stack.Screen name="TutRulesEdit" component={TutRulesEditScreen} />
      <Stack.Screen name="OnboardingDiagnosis" component={DiagnosisScreen} />
    </Stack.Navigator>
  );
}
