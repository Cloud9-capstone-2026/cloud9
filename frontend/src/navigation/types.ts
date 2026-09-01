export type TabParamList = {
  Home: undefined;
  ReportList: undefined;
  JournalList: undefined;
  MyPage: undefined;
  Settings: undefined;
};

export type CodeMode = 'signup' | 'reset' | 'changePw';
export type LegalKind = 'terms' | 'privacy';

export type AuthStackParamList = {
  Splash: undefined;
  Login: undefined;
  Signup: undefined;
  Verify: { mode: CodeMode };
  SignupDone: undefined;
  FindPw: undefined;
  ResetPw: { mode: CodeMode };
  SocialExtra: undefined;
  Legal: { kind: LegalKind };
};

export type OnboardingStackParamList = {
  Tutorial: undefined;
  TutRulesEdit: undefined;
  OnboardingDiagnosis: undefined;
};

export type RootStackParamList = {
  Tabs: undefined;
  ReportDetail: { tradeId: number };
  Upload: undefined;
  JournalFullList: undefined;
  JournalPending: undefined;
  JournalWrite: { journalId: number | null; tradeId?: number };
  NewsFullList: undefined;
  Diagnosis: undefined;
  Notifications: undefined;
  UploadHistory: undefined;
  Profile: undefined;
  ProfileVerify: { mode: CodeMode };
  ProfileResetPw: { mode: CodeMode };
  Legal: { kind: LegalKind };
  RulesSettings: undefined;
  Uploading: undefined;
  Analyzing: undefined;
  UploadDone: undefined;
  UploadFail: undefined;
  AnalyzeDone: undefined;
  AnalyzeFail: undefined;
};

declare global {
  // eslint-disable-next-line @typescript-eslint/no-namespace
  namespace ReactNavigation {
    interface RootParamList extends RootStackParamList {}
  }
}
