export type TabParamList = {
  Home: undefined;
  ReportList: undefined;
  JournalList: undefined;
  MyPage: undefined;
  Settings: undefined;
};

export type RootStackParamList = {
  Tabs: undefined;
  ReportDetail: { tradeId: number };
  Upload: undefined;
  JournalFullList: undefined;
  JournalWrite: { journalId: number | null };
  NewsFullList: undefined;
  Diagnosis: undefined;
};

declare global {
  // eslint-disable-next-line @typescript-eslint/no-namespace
  namespace ReactNavigation {
    interface RootParamList extends RootStackParamList {}
  }
}
