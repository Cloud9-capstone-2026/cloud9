import type {
  Trade, Journal, DartNews, UploadHistoryItem, MonthlyDatum,
  EmotionRadarDatum, BiasComparisonDatum, BiasTrendDatum, AnalysisEntry,
  RuleTemplate, TutorialStep, NotifRaw, LegalContent,
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
  { id: 6, corp: '현대차', type: '영업실적', title: '현대차 2026년 상반기 글로벌 판매 217만대 — 전년 동기 대비 4.2% 증가', date: '2026.08.04' },
  { id: 7, corp: '셀트리온', type: '단일판매계약', title: '셀트리온 유럽 바이오시밀러 공급계약 체결 — 계약금액 8,420억원', date: '2026.08.03' },
  { id: 8, corp: 'POSCO홀딩스', type: '투자판단', title: 'POSCO홀딩스 아르헨티나 리튬 2단계 생산설비 투자 결정', date: '2026.08.03' },
  { id: 9, corp: '삼성바이오로직스', type: '주요사항보고', title: '삼성바이오로직스 제5공장 준공 및 가동 개시 공시', date: '2026.08.02' },
  { id: 10, corp: '기아', type: '자기주식처분', title: '기아 자기주식 처분 결정 — 임직원 성과보상 목적 120만주', date: '2026.08.02' },
  { id: 11, corp: 'KB금융', type: '현금배당', title: 'KB금융 2026년 2분기 분기배당 결정 — 주당 795원', date: '2026.08.01' },
  { id: 12, corp: 'LG화학', type: '주요사항보고', title: 'LG화학 석유화학 부문 일부 사업 양도 검토 관련 조회공시 답변', date: '2026.08.01' },
  { id: 13, corp: '한화에어로스페이스', type: '단일판매계약', title: '한화에어로스페이스 폴란드 K9 자주포 2차 실행계약 체결', date: '2026.07.31' },
];

export const uploadHistoryRaw: UploadHistoryItem[] = [
  { id: 1, date: '2026.07.31', filename: 'trades_july_2026.csv', count: 18 },
  { id: 2, date: '2026.06.30', filename: 'trades_june_2026.csv', count: 11 },
  { id: 3, date: '2026.05.31', filename: 'trades_may_2026.csv', count: 15 },
  { id: 4, date: '2026.04.30', filename: 'trades_april_2026.csv', count: 9 },
  { id: 5, date: '2026.03.31', filename: 'trades_march_2026.csv', count: 14 },
  { id: 6, date: '2026.02.28', filename: 'trades_feb_2026.csv', count: 7 },
  { id: 7, date: '2026.01.31', filename: 'trades_jan_2026.csv', count: 12 },
  { id: 8, date: '2025.12.31', filename: 'trades_dec_2025.csv', count: 21 },
  { id: 9, date: '2025.11.30', filename: 'trades_nov_2025.csv', count: 8 },
  { id: 10, date: '2025.10.31', filename: 'trades_oct_2025.csv', count: 16 },
  { id: 11, date: '2025.09.30', filename: 'trades_sep_2025.csv', count: 10 },
  { id: 12, date: '2025.08.31', filename: 'trades_aug_2025.csv', count: 13 },
  { id: 13, date: '2025.07.31', filename: 'trades_july_2025.csv', count: 6 },
];

export const emotionRadarData: EmotionRadarDatum[] = [
  { e: '조급함', value: 4 }, { e: '욕심', value: 2 }, { e: '두려움', value: 1 },
  { e: '확신', value: 3 }, { e: '홧김', value: 0 }, { e: '미련', value: 1 },
  { e: '불안', value: 1 }, { e: '무심함', value: 0 }, { e: '후회', value: 2 }, { e: '흥분', value: 1 },
];

// 검사 결과(self) vs 실제 거래 데이터(trading) 비교 — 8/31 업데이트로 값 변경
export const biasComparisonData: BiasComparisonDatum[] = [
  { subject: '처분효과', self: 72, trading: 48 },
  { subject: '과잉확신', self: 38, trading: 69 },
  { subject: '복권형선호', self: 56, trading: 78 },
  { subject: '군집거래', self: 64, trading: 44 },
];

export const biasTrend: BiasTrendDatum[] = [
  { date: '3월', tested: true, 처분효과: 58, 과잉확신: 38, 복권형선호: 62, 군집거래: 52 },
  { date: '4월', tested: false, 처분효과: 58, 과잉확신: 38, 복권형선호: 62, 군집거래: 52 },
  { date: '5월', tested: true, 처분효과: 65, 과잉확신: 42, 복권형선호: 70, 군집거래: 58 },
  { date: '6월', tested: false, 처분효과: 65, 과잉확신: 42, 복권형선호: 70, 군집거래: 58 },
  { date: '7월', tested: true, 처분효과: 68, 과잉확신: 42, 복권형선호: 74, 군집거래: 61 },
];

export const BIAS_SCORES = [68, 42, 74, 61];

export const BIAS_DESCS = [
  '이익 난 종목은 서둘러 팔고, 손실 난 종목은 오래 붙잡는 경향이에요.',
  '자신의 판단을 과하게 믿어 필요 이상으로 자주 사고 파는 경향이에요.',
  '큰 수익 가능성만 보고 변동성이 큰 종목을 선호하는 경향이에요.',
  '다른 투자자들의 움직임이나 시장 분위기를 따라 사고파는 경향이에요.',
];

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
    rule_score: 0.70, stat_score: 0.31, deep_score: 0.46,
    detail: {
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
    rule_score: 0.85, stat_score: 0.78, deep_score: null,
    detail: {
      verdict: '이상', flags: { rule: true, stat: true }, layers_available: 2,
      triggered_rules: ['당일_왕복매매', '집중매매'], mahalanobis: 3.12, top_bias: 'overconfidence',
      bias_scores: { disposition_strength: 0.44, overconfidence: 0.85, lottery_preference: 0.22, herd_sensitivity: 0.61 },
      evidence: null,
    },
  },
  5: {
    rule_score: 0.91, stat_score: 0.88, deep_score: 0.76,
    detail: {
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

// ── 1계층 사용자 정의 규칙 템플릿 (7종) ────────────────────────
export const MONEY_LABEL = '상한 금액';

export const RULES: RuleTemplate[] = [
  { id: 'daily_frequency', name: '일중 반복매매', desc: '하루에 같은 종목을 여러 번 사고팔면 이상으로 봐요', unit: '회', label: '하루 같은 종목 매매 횟수', min: 2, max: 10, minL: '2회', maxL: '10회', defaultOn: true, defaultVal: 4 },
  { id: 'same_day_roundtrip', name: '당일 왕복매매', desc: '산 날에 바로 다시 파는 거래를 이상으로 봐요', unit: null, defaultOn: true, defaultVal: 0 },
  { id: 'min_holding', name: '최소 보유기간', desc: '정한 기간을 못 채우고 파는 거래를 이상으로 봐요', unit: '일', label: '최소 보유 일수', min: 1, max: 30, minL: '1일', maxL: '30일', defaultOn: false, defaultVal: 3 },
  { id: 'reentry_after_loss', name: '손실 후 재진입', desc: '손절한 종목을 곧바로 다시 사는 거래를 이상으로 봐요', unit: '일', label: '손절 후 재매수 기간', min: 1, max: 30, minL: '1일', maxL: '30일', defaultOn: false, defaultVal: 5 },
  { id: 'averaging_down', name: '물타기 반복', desc: '평균단가보다 낮은 가격에 반복 추가매수하면 이상으로 봐요', unit: '회', label: '추가매수 횟수', min: 2, max: 10, minL: '2회', maxL: '10회', defaultOn: false, defaultVal: 3 },
  { id: 'single_buy_cap', name: '1회 매수금액 상한', desc: '한 번에 이 금액을 넘게 사면 이상으로 봐요', unit: null, isMoney: true, label: '1회 매수금액 상한', defaultOn: false, defaultVal: 0 },
  { id: 'daily_total_cap', name: '일일 매매대금 상한', desc: '하루 매매대금이 이 금액을 넘으면 이상으로 봐요', unit: null, isMoney: true, label: '일일 매매대금 상한', defaultOn: false, defaultVal: 0 },
];

// ── 온보딩 튜토리얼 01~04 (05는 자가진단 유도 화면으로 별도 처리) ──
export const TUT: TutorialStep[] = [
  {
    kicker: '분석 리포트',
    title: '거래 하나하나를\n세 겹으로 검사해요',
    body: '내가 정한 규칙, 평소 패턴과의 차이, 그리고 AI 판단까지 — 세 계층이 각각 판정하고 근거까지 보여줘요.',
    points: ['규칙·통계·딥러닝 3계층 판정', '평소 패턴 대비 이탈도 표시', '판정에 영향을 준 요인 순위'],
  },
  {
    kicker: '거래일지',
    title: '그때 왜 그랬는지\n기록해두세요',
    body: '매매 이유와 당시 감정을 남기면, 실수가 반복되는 패턴을 스스로 발견할 수 있어요.',
    points: ['거래별 이유·감정·복기 기록', '감정 태그 10종으로 패턴 확인', '리포트와 바로 연결'],
  },
  {
    kicker: '성향 분석',
    title: '내 투자 성향,\n알면 대비할 수 \n있어요',
    body: '자가진단으로 내 투자 성향을 파악하고, 실제 거래 데이터와 비교해보면 미처 몰랐던 습관까지 발견할 수 있어요.',
    points: ['처분효과·과잉확신·복권형·군집거래', '검사 결과 vs 거래 기반 비교', '검사할수록 쌓이는 변화 추이'],
  },
  {
    kicker: '규칙 기반 탐지',
    title: '위험의 기준은\n직접 정해요',
    body: '사람마다 위험한 거래의 기준은 다릅니다. 7가지 규칙을 켜고 끄면서 내 기준을 만들면, 그 기준으로 거래를 검사해요.',
    points: ['하루 반복매매·당일 왕복매매 기본 적용', '보유기간·재진입·물타기 규칙 추가 가능', '금액 상한은 원화로 직접 입력'],
  },
];

// ── 알림 12건 ──────────────────────────────────────────────────
export const NOTIFS: NotifRaw[] = [
  { kind: 'analysis', file: 'trades_july_2026.csv', count: 69, time: '2026.07.31 14:22' },
  { kind: 'upload', file: 'trades_july_2026.csv', time: '2026.07.31 14:19' },
  { kind: 'analysis', file: 'trades_june_2026.csv', count: 51, time: '2026.06.30 09:41' },
  { kind: 'uploadFail', file: 'trades_june_2026.csv', time: '2026.06.14 20:05' },
  { kind: 'upload', file: 'trades_june_2026.csv', time: '2026.06.14 20:03' },
  { kind: 'analysis', file: 'trades_may_2026.csv', count: 44, time: '2026.05.31 11:28' },
  { kind: 'upload', file: 'trades_may_2026.csv', time: '2026.05.31 11:25' },
  { kind: 'analyzeFail', file: 'trades_may_2026.csv', time: '2026.05.12 18:40' },
  { kind: 'upload', file: 'trades_april_2026.csv', time: '2026.04.30 08:17' },
  { kind: 'analysis', file: 'trades_april_2026.csv', count: 29, time: '2026.04.30 08:20' },
  { kind: 'upload', file: 'trades_march_2026.csv', time: '2026.03.31 21:02' },
  { kind: 'analysis', file: 'trades_march_2026.csv', count: 17, time: '2026.03.31 21:05' },
];

// ── 약관 / 개인정보 처리방침 ────────────────────────────────────
export const LEGAL: Record<'terms' | 'privacy', LegalContent> = {
  terms: {
    title: '이용약관',
    meta: '시행일 2026년 7월 1일',
    sections: [
      { h: '제1조 (목적)', p: '본 약관은 Canary(이하 "회사")가 제공하는 투자 거래 분석 서비스(이하 "서비스")의 이용 조건 및 절차, 회사와 이용자의 권리·의무 및 책임사항을 규정함을 목적으로 합니다.' },
      { h: '제2조 (약관의 효력 및 변경)', p: '본 약관은 서비스 화면에 게시하거나 기타 방법으로 이용자에게 공지함으로써 효력이 발생합니다. 회사는 관련 법령을 위배하지 않는 범위에서 약관을 변경할 수 있으며, 변경 시 적용일자 및 변경사유를 명시하여 최소 7일 전에 공지합니다.' },
      { h: '제3조 (서비스의 내용)', p: '회사는 이용자가 업로드한 거래 내역을 바탕으로 다음 서비스를 제공합니다.\n\n1. 규칙·통계·딥러닝 기반 이상거래 탐지\n2. 투자 편향 분석 및 성향 자가진단\n3. 거래일지 기록 및 회고 기능' },
      { h: '제4조 (회원가입 및 탈퇴)', p: '이용자는 회사가 정한 절차에 따라 회원가입을 신청하며, 회사는 이를 승낙함으로써 이용계약이 성립합니다. 이용자는 언제든지 서비스 내 회원 탈퇴 기능을 통해 이용계약을 해지할 수 있습니다.' },
      { h: '제5조 (이용자의 의무)', p: '이용자는 타인의 거래 정보를 무단으로 업로드하거나, 서비스의 정상적인 운영을 방해하는 행위를 하여서는 안 됩니다. 계정 정보의 관리 책임은 이용자에게 있습니다.' },
      { h: '제6조 (투자 판단의 책임)', p: '본 서비스가 제공하는 모든 분석 결과와 지표는 이용자의 이해를 돕기 위한 참고 정보이며, 투자자문업 또는 투자권유에 해당하지 않습니다. 특정 종목의 매수·매도를 권유하지 않으며, 분석 결과에 기초한 투자 판단과 그 결과에 대한 책임은 전적으로 이용자에게 있습니다.' },
      { h: '제7조 (서비스의 중단)', p: '회사는 설비 점검·교체, 통신 장애, 천재지변 등 부득이한 사유가 발생한 경우 서비스 제공을 일시적으로 중단할 수 있으며, 이 경우 사전에 공지합니다.' },
      { h: '제8조 (지식재산권)', p: '서비스에 포함된 분석 모델, 화면 구성, 문구 등에 대한 지식재산권은 회사에 귀속됩니다. 이용자가 업로드한 거래 내역에 대한 권리는 이용자에게 있습니다.' },
      { h: '제9조 (분쟁의 해결)', p: '본 약관과 관련하여 분쟁이 발생한 경우 회사와 이용자는 상호 협의하여 해결하며, 협의가 이루어지지 않을 경우 민사소송법상의 관할 법원에 제소할 수 있습니다.' },
    ],
  },
  privacy: {
    title: '개인정보 처리방침',
    meta: '시행일 2026년 7월 1일',
    sections: [
      { h: '1. 수집하는 개인정보 항목', p: '회사는 서비스 제공을 위해 다음 정보를 수집합니다.\n\n· 필수 — 닉네임, 이메일 주소, 비밀번호(암호화 저장)\n· 서비스 이용 중 생성 — 업로드한 거래 내역(거래일자·종목명·거래구분·수량·단가), 거래일지 기록, 자가진단 응답, 탐지 규칙 설정값\n· 자동 수집 — 접속 일시, 기기 정보, 서비스 이용 기록' },
      { h: '2. 개인정보의 수집 및 이용 목적', p: '회원 식별 및 관리, 이상거래 탐지 및 편향 분석 결과 제공, 서비스 이용 통계 분석 및 품질 개선, 공지사항 전달 목적으로만 이용하며 그 외의 목적으로는 이용하지 않습니다.' },
      { h: '3. 개인정보의 보유 및 이용 기간', p: '회원 탈퇴 시 지체 없이 파기합니다. 단, 관련 법령에 따라 보존할 필요가 있는 경우 해당 기간 동안 보관합니다.\n\n· 계약 또는 청약철회 등에 관한 기록 — 5년\n· 접속에 관한 기록 — 3개월' },
      { h: '4. 개인정보의 제3자 제공', p: '회사는 이용자의 개인정보를 제3자에게 제공하지 않습니다. 다만 법령에 근거하여 수사기관의 적법한 요청이 있는 경우에는 예외로 합니다.' },
      { h: '5. 개인정보 처리의 위탁', p: '회사는 안정적인 서비스 제공을 위해 클라우드 인프라 운영 업무를 외부에 위탁하고 있으며, 위탁 계약 시 개인정보 보호 관련 사항을 명시하고 이를 관리·감독합니다.' },
      { h: '6. 개인정보의 파기 절차 및 방법', p: '보유 기간이 경과하거나 처리 목적이 달성된 개인정보는 지체 없이 파기합니다. 전자적 파일은 복구가 불가능한 방법으로 삭제하고, 출력물은 파쇄 또는 소각합니다.' },
      { h: '7. 이용자의 권리와 행사 방법', p: '이용자는 언제든지 자신의 개인정보에 대한 열람·정정·삭제·처리정지를 요구할 수 있습니다. 서비스 내 프로필 수정 화면 또는 개인정보 보호책임자에게 연락하여 행사할 수 있습니다.' },
      { h: '8. 개인정보의 안전성 확보 조치', p: '비밀번호는 일방향 암호화하여 저장하고, 거래 내역은 전송 구간과 저장 시점 모두 암호화합니다. 개인정보 처리 시스템에 대한 접근 권한은 업무상 필요한 최소한의 인원에게만 부여합니다.' },
      { h: '9. 개인정보 보호책임자', p: '· 책임자 — 개인정보보호팀\n· 이메일 — privacy@canary.app\n\n개인정보와 관련한 문의, 불만처리, 피해구제에 관한 사항을 담당하고 있습니다.' },
      { h: '10. 처리방침의 변경', p: '본 방침의 내용이 추가·삭제·수정되는 경우 변경사항의 시행 7일 전부터 서비스 내 공지사항을 통해 고지합니다.' },
    ],
  },
};
