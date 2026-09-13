// theme/tokens.ts의 PERIODS 문자열 → 일수. 백엔드 routers/news.py의 PERIOD_DAYS와 값 동기화.
const PERIOD_DAYS: Record<string, number> = {
  '최근 1개월': 30,
  '최근 3개월': 90,
  '최근 6개월': 180,
  '최근 1년': 365,
  '최근 3년': 365 * 3,
};

// dateStr은 ISO("2026-07-28"/타임스탬프) 또는 mock 포맷("2026.07.28") 둘 다 허용.
export function isWithinPeriod(dateStr: string, period: string): boolean {
  const days = PERIOD_DAYS[period];
  if (days == null) return true;
  const target = new Date(dateStr.replace(/\./g, '-'));
  if (Number.isNaN(target.getTime())) return true;
  const cutoff = new Date();
  cutoff.setHours(0, 0, 0, 0);
  cutoff.setDate(cutoff.getDate() - days);
  return target >= cutoff;
}
