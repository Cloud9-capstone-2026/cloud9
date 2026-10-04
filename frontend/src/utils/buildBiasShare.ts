import type { SurveyResult } from '../api/survey';
import type { AnalysisResult } from '../api/analysis';
import type { AccountBiasScoresResponse } from '../api/coach';
import { BIAS_KEYS, BiasKey } from '../theme/tokens';

// "검사 결과 vs 실제 거래" 카드 — 양쪽을 각자 100%로 환산해 구성을 비교한다.
// 점수끼리 직접 빼지 않는 이유: 자가진단 점수(설문 응답)와 거래 감지(모델 판정)는
// 산출 방식이 달라 같은 자로 잰 값이 아니다. 각자 자기 안에서 비중으로 바꾸면
// "몇 점부터 높음" 같은 기준을 새로 정하지 않고도 비교가 성립한다.

// 비중 차이가 이보다 작으면 "대체로 비슷"으로 본다(표시 기준 — 통계적 유의성 아님).
// 네 축이 100%를 나눠 가지니 평균 몫은 25%, 그 40%가 움직인 선.
export const SIMILAR_THRESHOLD = 10;

export type BiasShareStatus =
  | 'ok'              // 양쪽 다 비중이 있음
  | 'noSurvey'        // 자가진단 결과 없음
  | 'noTrades'        // 분석된 거래 없음
  | 'noDetection';    // 거래는 있지만 감지된 편향 0건

export interface BiasShareRow {
  key: BiasKey;
  /** 비교 대상에서 빠진 축(그 방향 거래가 0건이라 구조적으로 감지 불가) */
  excluded: boolean;
  self: number | null;
  trading: number | null;
  diff: number | null;
}

export interface BiasShareResult {
  status: BiasShareStatus;
  /** 막대에 그릴 축 — excluded를 제외한 것 */
  keys: BiasKey[];
  rows: BiasShareRow[];
  /** 감지된 편향 거래 수(아래 막대의 분모) */
  detectedCount: number;
  /** 제목에 쓸 축 — status가 'ok'이고 차이가 기준 이상일 때만 */
  headlineKey: BiasKey | null;
  headlineBigger: boolean;
  excludedKeys: BiasKey[];
}

// 합이 정확히 100이 되도록 정수화(최대잔여법) — 단순 반올림은 99나 101이 된다.
function toPercent(values: Record<string, number>, keys: BiasKey[]): Record<string, number> | null {
  const total = keys.reduce((sum, k) => sum + values[k], 0);
  if (total <= 0) return null;
  const exact = keys.map((k) => ({ key: k, value: (values[k] / total) * 100 }));
  const out: Record<string, number> = {};
  exact.forEach(({ key, value }) => { out[key] = Math.floor(value); });
  const remainder = 100 - keys.reduce((sum, k) => sum + out[k], 0);
  [...exact]
    .sort((a, b) => (b.value - Math.floor(b.value)) - (a.value - Math.floor(a.value)))
    .slice(0, remainder)
    .forEach(({ key }) => { out[key] += 1; });
  return out;
}

export function buildBiasShare(
  latestSurvey: SurveyResult | null,
  analysis: AnalysisResult[],
  accountScores: AccountBiasScoresResponse | null
): BiasShareResult {
  // 그 방향 거래가 한 건도 없는 축은 구조적으로 감지될 수 없다(처분효과는 매도,
  // 나머지 셋은 매수에서만 판정). 한쪽 막대에서만 빼면 남은 축 비중이 부풀려지므로
  // 양쪽에서 함께 빼고 나머지로 다시 100%를 잡는다.
  const excludedKeys = accountScores
    ? BIAS_KEYS.filter((k) => accountScores.scores[k]?.n_trades === 0)
    : [];
  const keys = BIAS_KEYS.filter((k) => !excludedKeys.includes(k));

  const detectCounts: Record<string, number> = Object.fromEntries(BIAS_KEYS.map((k) => [k, 0]));
  analysis.forEach((a) => {
    // 한글 라벨(top_bias_명)이 아니라 키로 센다 — 앱 안에 라벨 표기가 두 가지라 매칭이 깨질 수 있다.
    const key = a.detail.top_bias;
    if (key && a.detail.flags.deep) detectCounts[key] += 1;
  });
  const detectedCount = keys.reduce((sum, k) => sum + detectCounts[k], 0);

  const surveyValues = latestSurvey
    ? Object.fromEntries(BIAS_KEYS.map((k) => [k, latestSurvey.scores[k].normalized]))
    : null;
  const self = surveyValues ? toPercent(surveyValues, keys) : null;
  const trading = detectedCount > 0 ? toPercent(detectCounts, keys) : null;

  const status: BiasShareStatus =
    self == null ? 'noSurvey'
      : analysis.length === 0 ? 'noTrades'
        : trading == null ? 'noDetection'
          : 'ok';

  const rows: BiasShareRow[] = BIAS_KEYS.map((key) => ({
    key,
    excluded: excludedKeys.includes(key),
    self: self?.[key] ?? null,
    trading: trading?.[key] ?? null,
    diff: self && trading && !excludedKeys.includes(key) ? trading[key] - self[key] : null,
  }));

  let headlineKey: BiasKey | null = null;
  let headlineBigger = false;
  if (status === 'ok' && self && trading) {
    // 차이가 가장 큰 축 → 동점이면 실제 비중이 큰 쪽 → 그래도 같으면 BIAS_KEYS 순서.
    const best = [...keys].sort((a, b) => {
      const d = Math.abs(trading[b] - self[b]) - Math.abs(trading[a] - self[a]);
      if (d !== 0) return d;
      if (trading[b] !== trading[a]) return trading[b] - trading[a];
      return BIAS_KEYS.indexOf(a) - BIAS_KEYS.indexOf(b);
    })[0];
    const diff = trading[best] - self[best];
    if (Math.abs(diff) >= SIMILAR_THRESHOLD) {
      headlineKey = best;
      headlineBigger = diff > 0;
    }
  }

  return { status, keys, rows, detectedCount, headlineKey, headlineBigger, excludedKeys };
}

// "거래에서 가장 많이 나타난 편향" — top_bias_명(서버가 이미 한글로 준 라벨)의 최빈값.
// flags.deep이 true인(= 그 거래가 실제로 편향 임계값을 넘어 깃발 꽂힌) 거래만 센다.
// top_bias_명 자체는 3계층이 돌기만 하면 항상 채워지는 값(4개 편향 점수 중 최댓값을
// 그냥 뽑은 것)이라, 이것만으로 거르면 특별히 두드러진 편향이 없는 평범한 거래까지
// 섞여서 통계가 흐려진다.
export function computeTopBias(analysis: AnalysisResult[]): { label: string; count: number } | null {
  const counts: Record<string, number> = {};
  analysis.forEach((a) => {
    const label = a.detail.top_bias_명;
    if (label && a.detail.flags.deep) counts[label] = (counts[label] || 0) + 1;
  });
  let bestLabel: string | null = null;
  let bestCount = 0;
  Object.entries(counts).forEach(([label, c]) => {
    if (c > bestCount) { bestLabel = label; bestCount = c; }
  });
  return bestLabel ? { label: bestLabel, count: bestCount } : null;
}
