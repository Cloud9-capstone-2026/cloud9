import React from 'react';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import type { RootStackParamList } from './types';
import { TabNavigator } from './TabNavigator';
import { ReportDetailScreen } from '../screens/ReportDetailScreen';
import { UploadScreen } from '../screens/UploadScreen';
import { JournalFullListScreen } from '../screens/JournalFullListScreen';
import { JournalWriteScreen } from '../screens/JournalWriteScreen';
import { NewsFullListScreen } from '../screens/NewsFullListScreen';
import { DiagnosisScreen } from '../screens/DiagnosisScreen';

const Stack = createNativeStackNavigator<RootStackParamList>();

export function RootNavigator() {
  return (
    <Stack.Navigator screenOptions={{ headerShown: false }}>
      <Stack.Screen name="Tabs" component={TabNavigator} />
      <Stack.Screen name="ReportDetail" component={ReportDetailScreen} />
      <Stack.Screen name="Upload" component={UploadScreen} />
      <Stack.Screen name="JournalFullList" component={JournalFullListScreen} />
      <Stack.Screen name="JournalWrite" component={JournalWriteScreen} />
      <Stack.Screen name="NewsFullList" component={NewsFullListScreen} />
      <Stack.Screen name="Diagnosis" component={DiagnosisScreen} />
    </Stack.Navigator>
  );
}
