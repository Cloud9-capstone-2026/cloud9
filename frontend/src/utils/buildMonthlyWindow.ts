function monthKey(dateStr: string) {
  const d = new Date(dateStr);
  return d.getFullYear() * 12 + d.getMonth();
}

export interface MonthlyWindow {
  months: string[]; // 예: ['2월','3월',...,'7월'], 길이 windowSize
  tradeCounts: number[];
  anomalyCounts: number[];
}

// "전체 거래내역 중 가장 최근 거래월"을 기준으로 최근 windowSize개월 창을 만든다.
// 거래가 없는 달도 건너뛰지 않고 0으로 채운다. 두 그래프(월별 거래내역/이상 탐지 추이)가
// 같은 6개월 창을 공유하되, Y축 최댓값은 이 결과를 쓰는 쪽에서 각자 독립적으로 계산한다.
export function buildMonthlyWindow(
  tradeDates: string[],
  anomalyDates: string[],
  windowSize = 6
): MonthlyWindow {
  if (tradeDates.length === 0) {
    return { months: [], tradeCounts: [], anomalyCounts: [] };
  }
  const latestMonth = Math.max(...tradeDates.map(monthKey));

  const months: string[] = [];
  const tradeCounts: number[] = [];
  const anomalyCounts: number[] = [];
  for (let i = windowSize - 1; i >= 0; i--) {
    const key = latestMonth - i;
    const month = ((key % 12) + 12) % 12;
    months.push(`${month + 1}월`);
    tradeCounts.push(tradeDates.filter((d) => monthKey(d) === key).length);
    anomalyCounts.push(anomalyDates.filter((d) => monthKey(d) === key).length);
  }
  return { months, tradeCounts, anomalyCounts };
}
