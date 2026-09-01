import React from 'react';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import type { RootStackParamList } from './types';
import { TabNavigator } from './TabNavigator';
import { ReportDetailScreen } from '../screens/ReportDetailScreen';
import { UploadScreen } from '../screens/UploadScreen';
import { JournalFullListScreen } from '../screens/JournalFullListScreen';
import { JournalPendingScreen } from '../screens/JournalPendingScreen';
import { JournalWriteScreen } from '../screens/JournalWriteScreen';
import { NewsFullListScreen } from '../screens/NewsFullListScreen';
import { DiagnosisScreen } from '../screens/DiagnosisScreen';
import { NotificationsScreen } from '../screens/NotificationsScreen';
import { UploadHistoryScreen } from '../screens/UploadHistoryScreen';
import { ProfileScreen } from '../screens/ProfileScreen';
import { VerifyScreen } from '../screens/VerifyScreen';
import { ResetPwScreen } from '../screens/ResetPwScreen';
import { LegalScreen } from '../screens/LegalScreen';
import { RulesSettingsScreen } from '../screens/RulesSettingsScreen';
import { UploadingScreen } from '../screens/UploadingScreen';
import { AnalyzingScreen } from '../screens/AnalyzingScreen';
import { UploadDoneScreen } from '../screens/UploadDoneScreen';
import { UploadFailScreen } from '../screens/UploadFailScreen';
import { AnalyzeDoneScreen } from '../screens/AnalyzeDoneScreen';
import { AnalyzeFailScreen } from '../screens/AnalyzeFailScreen';
import { BiasInfoModal } from '../components/BiasInfoModal';
import { NotifPermissionModal } from '../components/NotifPermissionModal';

const Stack = createNativeStackNavigator<RootStackParamList>();

export function RootNavigator() {
  return (
    <>
      <Stack.Navigator screenOptions={{ headerShown: false }}>
        <Stack.Screen name="Tabs" component={TabNavigator} />
        <Stack.Screen name="ReportDetail" component={ReportDetailScreen} />
        <Stack.Screen name="Upload" component={UploadScreen} />
        <Stack.Screen name="JournalFullList" component={JournalFullListScreen} />
        <Stack.Screen name="JournalPending" component={JournalPendingScreen} />
        <Stack.Screen name="JournalWrite" component={JournalWriteScreen} />
        <Stack.Screen name="NewsFullList" component={NewsFullListScreen} />
        <Stack.Screen name="Diagnosis" component={DiagnosisScreen} />
        <Stack.Screen name="Notifications" component={NotificationsScreen} />
        <Stack.Screen name="UploadHistory" component={UploadHistoryScreen} />
        <Stack.Screen name="Profile" component={ProfileScreen} />
        <Stack.Screen name="ProfileVerify" component={VerifyScreen} />
        <Stack.Screen name="ProfileResetPw" component={ResetPwScreen} />
        <Stack.Screen name="Legal" component={LegalScreen} />
        <Stack.Screen name="RulesSettings" component={RulesSettingsScreen} />
        <Stack.Screen name="Uploading" component={UploadingScreen} options={{ gestureEnabled: false }} />
        <Stack.Screen name="Analyzing" component={AnalyzingScreen} options={{ gestureEnabled: false }} />
        <Stack.Screen name="UploadDone" component={UploadDoneScreen} options={{ gestureEnabled: false }} />
        <Stack.Screen name="UploadFail" component={UploadFailScreen} options={{ gestureEnabled: false }} />
        <Stack.Screen name="AnalyzeDone" component={AnalyzeDoneScreen} options={{ gestureEnabled: false }} />
        <Stack.Screen name="AnalyzeFail" component={AnalyzeFailScreen} options={{ gestureEnabled: false }} />
      </Stack.Navigator>
      <BiasInfoModal />
      <NotifPermissionModal />
    </>
  );
}
