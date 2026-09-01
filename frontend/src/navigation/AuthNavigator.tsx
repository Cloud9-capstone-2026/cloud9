import React from 'react';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import type { AuthStackParamList } from './types';
import { SplashScreen } from '../screens/SplashScreen';
import { LoginScreen } from '../screens/LoginScreen';
import { SignupScreen } from '../screens/SignupScreen';
import { VerifyScreen } from '../screens/VerifyScreen';
import { SignupDoneScreen } from '../screens/SignupDoneScreen';
import { FindPwScreen } from '../screens/FindPwScreen';
import { ResetPwScreen } from '../screens/ResetPwScreen';
import { SocialExtraScreen } from '../screens/SocialExtraScreen';
import { LegalScreen } from '../screens/LegalScreen';

const Stack = createNativeStackNavigator<AuthStackParamList>();

export function AuthNavigator() {
  return (
    <Stack.Navigator screenOptions={{ headerShown: false }}>
      <Stack.Screen name="Splash" component={SplashScreen} />
      <Stack.Screen name="Login" component={LoginScreen} />
      <Stack.Screen name="Signup" component={SignupScreen} />
      <Stack.Screen name="Verify" component={VerifyScreen} />
      <Stack.Screen name="SignupDone" component={SignupDoneScreen} />
      <Stack.Screen name="FindPw" component={FindPwScreen} />
      <Stack.Screen name="ResetPw" component={ResetPwScreen} />
      <Stack.Screen name="SocialExtra" component={SocialExtraScreen} />
      <Stack.Screen name="Legal" component={LegalScreen} />
    </Stack.Navigator>
  );
}
