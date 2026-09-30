import type { SurveyResult } from '../api/survey';
import type { AnalysisResult } from '../api/analysis';
import type { AccountBiasScoresResponse } from '../api/coach';
import type { BiasComparisonDatum } from '../data/types';
import { BIAS_KEYS, BiasKey } from '../theme/tokens';

// DumbbellChart/트렌드 쪽 subject 표기 컨벤션(공백 없음) — 기존 mock의 biasComparisonData와 동일 규칙.
const SUBJECT_LABEL: Record<BiasKey, string> = {
  disposition_strength: '처분효과',
  overconfidence: '과잉확신',
  lottery_preference: '복권형선호',
  herd_sensitivity: '군집거래',
};

// "검사 결과 vs 실제 거래 데이터" 비교 카드용 데이터.
// self(검사 결과) = 최근 자가진단의 normalized 점수(0~100) 그대로.
// trading(실제 거래 데이터) = 서버(GET /coach/scores)가 계산해서 주는 계좌 단위 편향 점수(0~100).
// 편향마다 의미 있는 매수/매도 방향의 거래만 평균 낸 값이라, 프론트에서 직접 전체 평균을
// 내는 것보다 정확하다(매수/매도 섞으면 반대쪽의 0에 가까운 값에 희석됨). 해당 방향
// 거래가 아예 없으면 서버가 score: null로 줌 — 0점과 구분해서 그대로 null을 전달한다.
export function buildBiasComparison(
  latestSurvey: SurveyResult | null,
  accountScores: AccountBiasScoresResponse | null
): BiasComparisonDatum[] {
  if (!latestSurvey) return [];

  return BIAS_KEYS.map((key) => {
    const self = Math.round(latestSurvey.scores[key].normalized);
    const trading = accountScores?.scores[key]?.score ?? null;
    return { subject: SUBJECT_LABEL[key], self, trading };
  });
}

// "최근 거래에서 가장 많이 나타난 편향" — top_bias_명(서버가 이미 한글로 준 라벨)의 최빈값.
export function computeTopBias(analysis: AnalysisResult[]): { label: string; count: number } | null {
  const counts: Record<string, number> = {};
  analysis.forEach((a) => {
    const label = a.detail.top_bias_명;
    if (label) counts[label] = (counts[label] || 0) + 1;
  });
  let bestLabel: string | null = null;
  let bestCount = 0;
  Object.entries(counts).forEach(([label, c]) => {
    if (c > bestCount) { bestLabel = label; bestCount = c; }
  });
  return bestLabel ? { label: bestLabel, count: bestCount } : null;
}
