import type { AnalysisResult } from '../api/analysis';
import type { SurveyResult } from '../api/survey';
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
// trading(실제 거래 데이터) = bias_scores가 있는(=3계층 다 판정된) 거래들의 평균을 ×100 — bias_scores 자체는
// 0~1 범위 내부 점수라 검사 결과와 같은 축 위에서 비교하려면 스케일을 맞춰야 한다.
// bias_scores가 null인 거래(딥러닝 계층 제외/미판정)는 평균에서 제외.
export function buildBiasComparison(
  latestSurvey: SurveyResult | null,
  analysis: AnalysisResult[]
): BiasComparisonDatum[] {
  if (!latestSurvey) return [];
  const withScores = analysis.filter((a) => a.detail.bias_scores != null);

  return BIAS_KEYS.map((key) => {
    const self = Math.round(latestSurvey.scores[key].normalized);
    let trading = 0;
    if (withScores.length > 0) {
      const sum = withScores.reduce(
        (acc, a) => acc + (a.detail.bias_scores as Record<BiasKey, number>)[key],
        0
      );
      trading = Math.round((sum / withScores.length) * 100);
    }
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
