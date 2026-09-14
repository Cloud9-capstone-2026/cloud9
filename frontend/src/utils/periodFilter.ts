import { parseServerDate } from './formatDate';

// theme/tokens.ts의 PERIODS 문자열 → 일수. 백엔드 routers/news.py의 PERIOD_DAYS와 값 동기화.
const PERIOD_DAYS: Record<string, number> = {
  '최근 1개월': 30,
  '최근 3개월': 90,
  '최근 6개월': 180,
  '최근 1년': 365,
  '최근 3년': 365 * 3,
};

// dateStr은 ISO("2026-07-28"/타임스탬프) 또는 mock 포맷("2026.07.28") 둘 다 허용. 시각까지
// 있는 진짜 타임스탬프는 소수점 이하 초(예: "16:10:23.123456")를 가질 수 있어서, 점을
// 대시로 바꾸는 건 "T"가 없는(= 시각 없는 mock 포맷일 때만) 적용한다 — 안 그러면 그 소수점을
// 잘못 건드려서 파싱이 깨진다.
export function isWithinPeriod(dateStr: string, period: string): boolean {
  const days = PERIOD_DAYS[period];
  if (days == null) return true;
  const normalized = dateStr.includes('T') ? dateStr : dateStr.replace(/\./g, '-');
  const target = parseServerDate(normalized);
  if (Number.isNaN(target.getTime())) return true;
  const cutoff = new Date();
  cutoff.setHours(0, 0, 0, 0);
  cutoff.setDate(cutoff.getDate() - days);
  return target >= cutoff;
}
