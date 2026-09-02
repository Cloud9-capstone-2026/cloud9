import { createNavigationContainerRef } from '@react-navigation/native';
import type { RootStackParamList, LegalKind } from './types';

export const navigationRef = createNavigationContainerRef<RootStackParamList>();

export function goToUpload() {
  if (navigationRef.isReady()) navigationRef.navigate('Upload');
}

export function goToTab(tab: 'Home' | 'ReportList' | 'JournalList' | 'MyPage' | 'Settings') {
  if (navigationRef.isReady()) {
    navigationRef.navigate('Tabs', { screen: tab } as never);
  }
}

export function goToReportDetail(tradeId: number) {
  if (navigationRef.isReady()) navigationRef.navigate('ReportDetail', { tradeId });
}

export function goToJournalWrite(journalId: number | null, tradeId?: number) {
  if (navigationRef.isReady()) navigationRef.navigate('JournalWrite', { journalId, tradeId });
}

export function goToJournalFullList() {
  if (navigationRef.isReady()) navigationRef.navigate('JournalFullList');
}

export function goToJournalPending() {
  if (navigationRef.isReady()) navigationRef.navigate('JournalPending');
}

export function goToNewsFullList() {
  if (navigationRef.isReady()) navigationRef.navigate('NewsFullList');
}

export function goToDiagnosis() {
  if (navigationRef.isReady()) navigationRef.navigate('Diagnosis');
}

export function goToNotifications() {
  if (navigationRef.isReady()) navigationRef.navigate('Notifications');
}

export function goToUploadHistory() {
  if (navigationRef.isReady()) navigationRef.navigate('UploadHistory');
}

export function goToProfile() {
  if (navigationRef.isReady()) navigationRef.navigate('Profile');
}

export function goToLegal(kind: LegalKind) {
  if (navigationRef.isReady()) navigationRef.navigate('Legal', { kind, variant: 'app' });
}

export function goToRulesSettings() {
  if (navigationRef.isReady()) navigationRef.navigate('RulesSettings');
}

export function goToUploading() {
  if (navigationRef.isReady()) navigationRef.navigate('Uploading');
}

export function goToAnalyzing() {
  if (navigationRef.isReady()) navigationRef.navigate('Analyzing');
}
