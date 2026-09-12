export type TabParamList = {
  Home: undefined;
  ReportList: undefined;
  JournalList: undefined;
  MyPage: undefined;
  Settings: undefined;
};

// 'changePw'는 더 이상 이메일 인증코드 화면을 쓰지 않음(로그인 상태에서 현재
// 비밀번호로 바로 바꾸는 방식으로 변경 — ChangePasswordScreen 참고) — CodeMode에서 제외.
export type CodeMode = 'signup' | 'reset';
export type LegalKind = 'terms' | 'privacy';

export type AuthStackParamList = {
  Splash: undefined;
  Login: undefined;
  Signup: undefined;
  Verify: { mode: CodeMode; email: string };
  SignupDone: undefined;
  FindPw: undefined;
  ResetPw: { email: string; code: string };
  SocialExtra: undefined;
  Legal: { kind: LegalKind; variant: 'auth' | 'app' };
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
  ChangePassword: undefined;
  Legal: { kind: LegalKind; variant: 'auth' | 'app' };
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
