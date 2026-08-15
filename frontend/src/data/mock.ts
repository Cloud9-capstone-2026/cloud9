import type {
  Trade, Journal, DartNews, UploadHistoryItem, MonthlyDatum,
  EmotionRadarDatum, BiasComparisonDatum, BiasTrendDatum, AnalysisEntry,
} from './types';

export const tradesRaw: Trade[] = [
  { id: 1, stock: '삼성전자', date: '2026.07.28', type: 'buy', price: '65,000', qty: 50, amount: '3,250,000', score: 78, deviation: 2.84 },
  { id: 2, stock: 'SK하이닉스', date: '2026.07.25', type: 'sell', price: '206,000', qty: 20, amount: '4,118,000', score: 22, deviation: 0.91 },
  { id: 3, stock: 'NAVER', date: '2026.07.22', type: 'buy', price: '175,000', qty: 10, amount: '1,749,000', score: 85, deviation: 3.12 },
  { id: 4, stock: '카카오', date: '2026.07.18', type: 'sell', price: '43,000', qty: 20, amount: '859,500', score: 52, deviation: 1.62 },
  { id: 5, stock: 'LG에너지솔루션', date: '2026.07.15', type: 'buy', price: '345,000', qty: 20, amount: '6,896,000', score: 91, deviation: 3.88 },
  { id: 6, stock: '현대차', date: '2026.07.10', type: 'buy', price: '206,000', qty: 10, amount: '2,059,000', score: 45, deviation: 1.10 },
  { id: 7, stock: '포스코퓨처엠', date: '2026.07.05', type: 'buy', price: '280,000', qty: 5, amount: '1,399,000', score: 67, deviation: 1.90 },
  { id: 8, stock: '에코프로비엠', date: '2026.07.02', type: 'sell', price: '163,000', qty: 15, amount: '2,444,000', score: 31, deviation: 0.80 },
  { id: 9, stock: '고려아연', date: '2026.06.28', type: 'buy', price: '610,000', qty: 3, amount: '1,829,000', score: 74, deviation: 2.20 },
  { id: 10, stock: 'POSCO홀딩스', date: '2026.06.25', type: 'sell', price: '390,000', qty: 8, amount: '3,119,000', score: 48, deviation: 1.30 },
  { id: 11, stock: '두산에너빌리티', date: '2026.06.22', type: 'buy', price: '24,000', qty: 100, amount: '2,399,000', score: 82, deviation: 3.40 },
  { id: 12, stock: '한화에어로스페이스', date: '2026.06.18', type: 'buy', price: '195,000', qty: 10, amount: '1,949,000', score: 37, deviation: 0.95 },
];

export const monthlyData: MonthlyDatum[] = [
  { month: '2월', trades: 8, anomalies: 3 },
  { month: '3월', trades: 12, anomalies: 5 },
  { month: '4월', trades: 7, anomalies: 2 },
  { month: '5월', trades: 15, anomalies: 8 },
  { month: '6월', trades: 11, anomalies: 4 },
  { month: '7월', trades: 18, anomalies: 9 },
];

export const journals: Journal[] = [
  { id: 1, stock: '삼성전자', date: '2026.07.28', type: 'buy', emotion: '확신', risk: 'danger', memo: '실적 개선 기대감으로 매수.', reason: '2분기 영업이익이 시장 기대치를 상회했고 HBM 수주가 가속화되는 상황. 반도체 슈퍼사이클 진입 시그널로 판단해 매수.', review: '매수 직후 2.3% 하락했으나 이후 회복. 장기적 관점에서는 올바른 판단이었다고 생각.' },
  { id: 2, stock: 'SK하이닉스', date: '2026.07.25', type: 'sell', emotion: '안도', risk: 'safe', memo: 'HBM 공급 우려 뉴스 후 일부 정리.', reason: 'HBM 4 공급 과잉 우려 보도가 연속으로 나와 리스크 관리 차원에서 일부 매도.', review: '매도 후 주가가 추가 상승해 아쉬움. 리스크 관리 원칙은 잘 지켰다.' },
  { id: 3, stock: 'NAVER', date: '2026.07.22', type: 'buy', emotion: '조급함', risk: 'danger', memo: '주가 급등 전 탑승하려 서두름.', reason: 'AI 검색 서비스 업데이트 소식에 급등이 예상되어 빠르게 진입. 충분한 분석 없이 진입.', review: '고점에 가까운 지점에서 매수. 조급함이 판단을 흐렸다.' },
  { id: 4, stock: '카카오', date: '2026.07.18', type: 'sell', emotion: '후회', risk: 'caution', memo: '더 오를 것 같은데 손절. 원칙에 따라 처분.', reason: '손절 기준선(-8%) 도달. 원칙에 따라 손절했으나 이후 반등이 아쉬움.', review: '손절 원칙을 지킨 것은 맞으나, 단기 패닉 상황이었을 가능성이 있다.' },
  { id: 5, stock: 'LG에너지솔루션', date: '2026.07.15', type: 'buy', emotion: '욕심', risk: 'danger', memo: '수익 극대화 목적의 고위험 집중 매수.', reason: '전기차 시장 회복 기대로 대규모 매수. 포트폴리오 비중을 크게 초과.', review: '단일 종목 비중이 너무 높아졌다. 분산투자 원칙을 어긴 것이 우려됨.' },
];

export const dartNews: DartNews[] = [
  { id: 1, corp: '삼성전자', type: '분기보고서', title: '삼성전자 2026년 2분기 연결 재무제표 기준 영업이익 18.9조원 달성', date: '2026.08.06' },
  { id: 2, corp: 'SK하이닉스', type: '주요사항보고', title: 'SK하이닉스, HBM4 양산 일정 공식 확인 및 NVIDIA 공급 계약 연장 발표', date: '2026.08.06' },
  { id: 3, corp: 'LG에너지솔루션', type: '자기주식취득', title: 'LG에너지솔루션 자기주식 취득 결정 — 500만주 1조 5,000억원 규모', date: '2026.08.05' },
  { id: 4, corp: 'NAVER', type: '임원퇴임', title: 'NAVER 최수연 대표이사 임기만료에 따른 이사회 결의 및 신임 대표 선임', date: '2026.08.05' },
  { id: 5, corp: '카카오', type: '유상증자', title: '카카오 제3자배정 유상증자 결정 — 글로벌 AI 파트너십 강화 목적', date: '2026.08.04' },
];

export const uploadHistoryRaw: UploadHistoryItem[] = [
  { id: 1, date: '2026.07.31', filename: 'trades_july_2026.csv', count: 18 },
  { id: 2, date: '2026.06.30', filename: 'trades_june_2026.csv', count: 11 },
  { id: 3, date: '2026.05.31', filename: 'trades_may_2026.csv', count: 15 },
];

export const emotionRadarData: EmotionRadarDatum[] = [
  { e: '조급함', value: 4 }, { e: '욕심', value: 2 }, { e: '두려움', value: 1 },
  { e: '확신', value: 3 }, { e: '홧김', value: 0 }, { e: '미련', value: 1 },
  { e: '불안', value: 1 }, { e: '무심함', value: 0 }, { e: '후회', value: 2 }, { e: '흥분', value: 1 },
];

export const biasComparisonData: BiasComparisonDatum[] = [
  { subject: '처분효과', self: 65, trading: 68 },
  { subject: '과잉확신', self: 45, trading: 42 },
  { subject: '복권형선호', self: 70, trading: 74 },
  { subject: '군집거래', self: 58, trading: 61 },
];

export const biasTrend: BiasTrendDatum[] = [
  { date: '3월', tested: true, 처분효과: 58, 과잉확신: 38, 복권형선호: 62, 군집거래: 52 },
  { date: '4월', tested: false, 처분효과: 58, 과잉확신: 38, 복권형선호: 62, 군집거래: 52 },
  { date: '5월', tested: true, 처분효과: 65, 과잉확신: 42, 복권형선호: 70, 군집거래: 58 },
  { date: '6월', tested: false, 처분효과: 65, 과잉확신: 42, 복권형선호: 70, 군집거래: 58 },
  { date: '7월', tested: true, 처분효과: 68, 과잉확신: 42, 복권형선호: 74, 군집거래: 61 },
];

export const BIAS_SCORES = [68, 42, 74, 61];

export const QUESTIONS: string[] = [
  '수익이 조금이라도 나면, 더 오를 수 있어도 일단 팔아서 이익을 확정하고 싶다.',
  '손실 중인 종목은 손실을 확정하기 싫어서 계속 들고 있는 편이다.',
  '나는 오른 종목보다 내린 종목을 더 오래 보유하는 경향이 있다.',
  '손실이 나면 "다시 오를 때까지 기다리자"고 스스로를 설득하곤 한다.',
  '목표 수익률에 도달하지 않았어도, 손실 여부와 상관없이 계획한 시점에 매도하는 편이다.',
  '내 투자 판단은 대체로 다른 투자자들보다 정확하다고 생각한다.',
  '수익이 났을 때는 내 실력이나 분석 덕분이라고 생각하는 편이다.',
  '손실이 났을 때는 운이 나빴거나 시장 상황 탓이라고 생각하는 편이다.',
  '주가가 오르는 시기엔 평소보다 더 자주 거래하고 싶어진다.',
  '내가 잘 안다고 생각하는 종목이라도, 내 판단이 틀릴 수 있다고 자주 생각한다.',
  '적은 돈으로 크게 오를 수 있는 종목에 끌린다.',
  '주가가 낮은 종목(이른바 "동전주")에 관심이 가는 편이다.',
  '하루 만에 급등할 것 같은 종목을 종종 매수한다.',
  '안정적으로 조금씩 오르는 종목보다 크게 오르내리는 종목이 더 흥미롭다.',
  '여러 종목에 나눠 투자하기보다 소수 종목에 집중하는 편이다.',
  '요즘 화제가 되는 종목이면 나도 사보고 싶어진다.',
  '다른 사람들이 많이 사는 종목을 보면 나도 사야 할 것 같은 기분이 든다.',
  '급등 중인 종목을 보면 놓칠까봐 따라서 매수한 적이 있다.',
  '커뮤니티나 지인이 추천한 종목을 스스로 분석하지 않고 매수한 적이 있다.',
  '다른 사람들이 어떤 종목을 사고팔든 내 투자 결정에는 영향을 주지 않는다.',
];

export const analysisData: Record<number, AnalysisEntry> = {
  1: {
    rule_score: 0.70, stat_score: 0.31, lstm_score: 0.46,
    xai_result: {
      verdict: '경고', flags: { rule: true, stat: false, deep: false }, layers_available: 3,
      triggered_rules: ['당일_왕복매매'], mahalanobis: 1.42, top_bias: 'herd_sensitivity',
      bias_scores: { disposition_strength: 0.12, overconfidence: 0.31, lottery_preference: 0.05, herd_sensitivity: 0.46 },
      evidence: {
        disposition_strength: { trade_share: 0.61, context_share: 0.39, features: [{ feature: '매도실현수익률', attribution: -31.55 }, { feature: '비정상거래량', attribution: 1.38 }, { feature: '보유기간', attribution: -2.10 }] },
        overconfidence: { trade_share: 0.55, context_share: 0.45, features: [{ feature: '거래금액', attribution: 14.20 }, { feature: '최근5일수익률', attribution: 8.30 }, { feature: '매수여부', attribution: -3.10 }] },
        lottery_preference: { trade_share: 0.48, context_share: 0.52, features: [{ feature: '복권성순위', attribution: 22.10 }, { feature: '지수수익률', attribution: -4.50 }, { feature: '전일수익률', attribution: 2.80 }] },
        herd_sensitivity: { trade_share: 0.70, context_share: 0.30, features: [{ feature: '비정상거래량', attribution: 38.20 }, { feature: '직전거래간격', attribution: -12.40 }, { feature: '지수수익률', attribution: 9.10 }, { feature: '거래금액', attribution: -3.20 }] },
      },
    },
  },
  3: {
    rule_score: 0.85, stat_score: 0.78, lstm_score: null,
    xai_result: {
      verdict: '이상', flags: { rule: true, stat: true }, layers_available: 2,
      triggered_rules: ['당일_왕복매매', '집중매매'], mahalanobis: 3.12, top_bias: 'overconfidence',
      bias_scores: { disposition_strength: 0.44, overconfidence: 0.85, lottery_preference: 0.22, herd_sensitivity: 0.61 },
      evidence: null,
    },
  },
  5: {
    rule_score: 0.91, stat_score: 0.88, lstm_score: 0.76,
    xai_result: {
      verdict: '이상', flags: { rule: true, stat: true, deep: true }, layers_available: 3,
      triggered_rules: ['집중매매', '반복매수'], mahalanobis: 3.88, top_bias: 'overconfidence',
      bias_scores: { disposition_strength: 0.55, overconfidence: 0.91, lottery_preference: 0.38, herd_sensitivity: 0.72 },
      evidence: {
        disposition_strength: { trade_share: 0.60, context_share: 0.40, features: [{ feature: '보유기간', attribution: -18.20 }, { feature: '매도실현수익률', attribution: 12.30 }] },
        overconfidence: { trade_share: 0.78, context_share: 0.22, features: [{ feature: '거래금액', attribution: 55.10 }, { feature: '비정상거래량', attribution: 22.40 }, { feature: '최근5일수익률', attribution: 14.20 }, { feature: '직전거래간격', attribution: -6.80 }] },
        lottery_preference: { trade_share: 0.50, context_share: 0.50, features: [{ feature: '복권성순위', attribution: 18.30 }, { feature: '전일수익률', attribution: 5.40 }] },
        herd_sensitivity: { trade_share: 0.65, context_share: 0.35, features: [{ feature: '지수수익률', attribution: 28.10 }, { feature: '비정상거래량', attribution: 14.30 }, { feature: '직전거래간격', attribution: -8.20 }] },
      },
    },
  },
};
