import type { SurveyResult } from '../api/survey';
import type { BiasTrendDatum } from '../data/types';
import { parseServerDate } from './formatDate';

function monthKey(iso: string) {
  const d = parseServerDate(iso);
  return d.getFullYear() * 12 + d.getMonth();
}

// 검사 히스토리(GET /survey/history, 아무 순서)를 "검사 히스토리" 그래프용 5개월치
// 배열로 변환한다.
// - 가장 최근 검사가 있었던 달이 항상 배열 맨 끝(그래프 오른쪽 끝)이 된다.
// - 그 달에 실제 검사가 있으면 채워진 점(tested:true), 없지만 그 이전에 검사 이력이
//   있으면 직전 검사값을 이어온 빈 점(tested:false), 그 이전에 검사 이력이 아예
//   없으면(첫 검사 이전) 값 자체를 null로 둬서 점을 안 그리게 한다.
// - 같은 달에 여러 번 검사했으면 그중 가장 최근 것을 그 달의 값으로 쓴다.
export function buildBiasTrend(history: SurveyResult[], windowSize = 5): BiasTrendDatum[] {
  const sorted = [...history].sort(
    (a, b) => parseServerDate(a.created_at).getTime() - parseServerDate(b.created_at).getTime()
  );
  // 검사 이력이 아예 없으면(정상 플로우에선 온보딩 때 최소 1회 강제라 드문 경우) 현재
  // 달을 기준으로 5개월 창을 만들되, 값은 전부 null이라 점 없는 빈 그래프가 된다.
  const latestMonth = sorted.length > 0
    ? monthKey(sorted[sorted.length - 1].created_at)
    : monthKey(new Date().toISOString());

  const rows: BiasTrendDatum[] = [];
  for (let i = windowSize - 1; i >= 0; i--) {
    const key = latestMonth - i;
    const month = ((key % 12) + 12) % 12;

    const inMonth = sorted.filter((r) => monthKey(r.created_at) === key);
    const latestInMonth = inMonth[inMonth.length - 1] ?? null;
    const before = sorted.filter((r) => monthKey(r.created_at) < key);
    const latestBefore = before[before.length - 1] ?? null;

    const source = latestInMonth ?? latestBefore;
    rows.push({
      date: `${month + 1}월`,
      tested: !!latestInMonth,
      처분효과: source ? source.scores.disposition_strength.normalized : null,
      과잉확신: source ? source.scores.overconfidence.normalized : null,
      복권형선호: source ? source.scores.lottery_preference.normalized : null,
      군집거래: source ? source.scores.herd_sensitivity.normalized : null,
    });
  }
  return rows;
}
