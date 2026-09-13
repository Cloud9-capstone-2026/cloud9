export type TradeType = 'buy' | 'sell';

export interface Trade {
  id: number;
  stock: string;
  date: string;
  type: TradeType;
  price: string;
  qty: number;
  amount: string;
  score: number;
  deviation: number;
}

export interface DartNews {
  id: number;
  corp: string;
  type: string;
  title: string;
  date: string;
}

export interface BiasComparisonDatum {
  subject: string;
  self: number;
  trading: number;
}

export interface BiasTrendDatum {
  date: string;
  // tested=true(그 달에 실제 검사) → 채워진 점, false(직전 검사값을 이어옴) → 빈 점,
  // 값 자체가 null(그 달 이전엔 검사 이력이 아예 없음) → 점을 그리지 않음.
  tested: boolean;
  처분효과: number | null;
  과잉확신: number | null;
  복권형선호: number | null;
  군집거래: number | null;
}

// ── 1계층 사용자 정의 규칙 템플릿 ──────────────────────────────
export interface RuleTemplate {
  id: string;
  name: string;
  desc: string;
  unit: '회' | '일' | null;
  label?: string;
  min?: number;
  max?: number;
  minL?: string;
  maxL?: string;
  isMoney?: boolean;
  defaultOn: boolean;
  defaultVal: number;
}

// ── 온보딩 튜토리얼 ────────────────────────────────────────────
export interface TutorialStep {
  kicker: string;
  title: string;
  body: string;
  points: string[];
}

// ── 알림 ──────────────────────────────────────────────────────
export type NotifKind = 'analysis' | 'upload' | 'uploadFail' | 'analyzeFail';
export interface NotifRaw {
  kind: NotifKind;
  file: string;
  count?: number;
  time: string;
}

// ── 약관/개인정보 ──────────────────────────────────────────────
export interface LegalSection {
  h: string;
  p: string;
}
export interface LegalContent {
  title: string;
  sections: LegalSection[];
}
