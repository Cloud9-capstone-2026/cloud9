import { createNavigationContainerRef } from '@react-navigation/native';
import type { RootStackParamList } from './types';

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

export function goToJournalWrite(journalId: number | null) {
  if (navigationRef.isReady()) navigationRef.navigate('JournalWrite', { journalId });
}

export function goToJournalFullList() {
  if (navigationRef.isReady()) navigationRef.navigate('JournalFullList');
}

export function goToNewsFullList() {
  if (navigationRef.isReady()) navigationRef.navigate('NewsFullList');
}

export function goToDiagnosis() {
  if (navigationRef.isReady()) navigationRef.navigate('Diagnosis');
}
