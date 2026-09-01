export const C = {
  bg: '#F7F8FA',
  card: '#FFFFFF',
  navy: '#16213b',
  black: '#111111',
  blue: '#0066FF',
  blueLight: '#e8f0ff',
  red: '#dc2626',
  border: '#e8edf4',
  muted: '#94a3b8',
  mutedBg: '#f1f5f9',
  subtleBg: '#f8fafc',
  white: '#ffffff',
};

export const ACCENT = '#FACC15';

export const RISK = {
  danger: { label: '이상', color: '#AE77FF', bg: '#F5EEFF', ring: '#AE77FF' },
  caution: { label: '경고', color: '#FFB800', bg: '#FFF8E0', ring: '#FFB800' },
  safe: { label: '정상', color: '#009905', bg: '#E6FFE7', ring: '#00C807' },
} as const;

export type RiskLevel = keyof typeof RISK;

export function riskLevel(score: number): RiskLevel {
  return score >= 70 ? 'danger' : score >= 40 ? 'caution' : 'safe';
}

export const BIAS_COLORS = ['#0066FF', '#4F46E5', '#0891B2', '#64748B'];
export const BIAS_LABELS = ['처분효과', '과잉확신', '복권형 선호', '군집거래'];
export const BIAS_TREND_KEYS = ['처분효과', '과잉확신', '복권형선호', '군집거래'] as const;
export const BIAS_KEYS = [
  'disposition_strength',
  'overconfidence',
  'lottery_preference',
  'herd_sensitivity',
] as const;
export type BiasKey = (typeof BIAS_KEYS)[number];
export const BIAS_KEY_MAP: Record<BiasKey, string> = {
  disposition_strength: '처분효과',
  overconfidence: '과잉확신',
  lottery_preference: '복권형 선호',
  herd_sensitivity: '군집거래',
};
export function biasColorOf(key: BiasKey) {
  return BIAS_COLORS[BIAS_KEYS.indexOf(key)];
}

export const LAYER_RING = { detected: '#F03E3E', undetected: '#c8d2dc' };
export const DEVIATION_GAUGE = ['#D1D5DB', '#FCA5A5', '#F87171', '#EF4444'];

export const EMOTIONS = [
  '조급함', '욕심', '두려움', '확신', '홧김', '미련', '불안', '무심함', '후회', '흥분',
];

export const FEATURE_POOL = [
  '거래금액', '비정상거래량', '매도실현수익률', '보유기간', '최근5일수익률',
  '복권성순위', '지수수익률', '전일수익률', '직전거래간격', '매수여부',
];

export const PERIODS = ['최근 1개월', '최근 3개월', '최근 6개월', '최근 1년', '최근 3년'];

export const spacing = {
  screenPaddingH: 22,
  diagnosisPaddingH: 28,
  cardRadius: 30,
  smallCardRadius: 26,
  chipRadius: 20,
  evidenceListRadius: 14,
  toggleRadius: 12,
  pillRadius: 999,
  cardPadding: 16,
  cardPaddingSmall: 14,
  sectionGap: 24,
};

export const shadow = {
  header: {
    shadowColor: '#16213b',
    shadowOpacity: 0.07,
    shadowOffset: { width: 0, height: 2 },
    shadowRadius: 10,
    elevation: 2,
  },
  floating: {
    shadowColor: '#16213b',
    shadowOpacity: 0.1,
    shadowOffset: { width: 0, height: 4 },
    shadowRadius: 18,
    elevation: 6,
  },
  ctaBlue: {
    shadowColor: '#0066FF',
    shadowOpacity: 0.27,
    shadowOffset: { width: 0, height: 4 },
    shadowRadius: 16,
    elevation: 8,
  },
  modal: {
    shadowColor: 'rgba(16,24,40,1)',
    shadowOpacity: 0.22,
    shadowOffset: { width: 0, height: 12 },
    shadowRadius: 40,
    elevation: 16,
  },
  dropdown: {
    shadowColor: '#16213b',
    shadowOpacity: 0.14,
    shadowOffset: { width: 0, height: 6 },
    shadowRadius: 22,
    elevation: 10,
  },
};

export const text = {
  screenTitle: { fontSize: 22, fontWeight: '600' as const, letterSpacing: -0.3, lineHeight: 28, color: C.navy },
  screenSubtitle: { fontSize: 15, fontWeight: '400' as const, color: C.muted, lineHeight: 20 },
  sectionTitle: { fontSize: 20, fontWeight: '600' as const, letterSpacing: -0.1, color: C.navy },
  cardSubtitle: { fontSize: 13, fontWeight: '500' as const, color: C.navy },
  mutedLabel: { fontSize: 12, fontWeight: '400' as const, color: C.muted },
};
