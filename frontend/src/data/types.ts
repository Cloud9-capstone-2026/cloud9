import type { RiskLevel } from '../theme/tokens';

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

export interface TradeWithRisk extends Trade {
  risk: RiskLevel;
}

export interface Journal {
  id: number;
  stock: string;
  date: string;
  type: TradeType;
  emotion: string;
  risk: RiskLevel;
  memo: string;
  reason: string;
  review: string;
}

export interface DartNews {
  id: number;
  corp: string;
  type: string;
  title: string;
  date: string;
}

export interface UploadHistoryItem {
  id: number;
  date: string;
  filename: string;
  count: number;
}

export interface MonthlyDatum {
  month: string;
  trades: number;
  anomalies: number;
}

export interface EmotionRadarDatum {
  e: string;
  value: number;
}

export interface BiasComparisonDatum {
  subject: string;
  self: number;
  trading: number;
}

export interface BiasTrendDatum {
  date: string;
  tested: boolean;
  처분효과: number;
  과잉확신: number;
  복권형선호: number;
  군집거래: number;
}

export interface EvidenceFeature {
  feature: string;
  attribution: number;
}

export interface EvidenceEntry {
  trade_share: number;
  context_share: number;
  features: EvidenceFeature[];
}

export interface XaiResult {
  verdict: '정상' | '경고' | '이상';
  flags: { rule: boolean; stat: boolean; deep?: boolean };
  layers_available: number;
  triggered_rules: string[];
  mahalanobis: number;
  top_bias: string;
  bias_scores: Record<string, number>;
  evidence: Record<string, EvidenceEntry> | null;
}

export interface AnalysisEntry {
  rule_score: number;
  stat_score: number;
  lstm_score: number | null;
  xai_result: XaiResult;
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
