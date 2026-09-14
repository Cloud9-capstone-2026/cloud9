// 백엔드가 시각(TIMESTAMP) 컬럼을 타임존 표시 없이 내려주는데, 실제 값은 UTC라서
// (DB가 UTC 기준으로 now()를 채움) 그냥 new Date()로 파싱하면 브라우저가 이걸 이미
// 로컬시간인 것처럼 취급해버려 실제보다 9시간(KST) 이르게(전날 오후처럼) 보인다.
// "T"가 있는(시각 포함) 문자열인데 타임존 표시(Z/±HH:MM)가 없으면 UTC로 간주해서
// 보정한다 — 날짜만 있는 문자열("2026-07-28")은 원래도 안전해서 손대지 않는다.
export function parseServerDate(iso: string): Date {
  const hasTime = iso.includes('T');
  const hasTz = /Z$|[+-]\d{2}:?\d{2}$/.test(iso);
  return new Date(hasTime && !hasTz ? `${iso}Z` : iso);
}

export function formatDate(iso: string) {
  const d = parseServerDate(iso);
  return `${d.getFullYear()}.${String(d.getMonth() + 1).padStart(2, '0')}.${String(d.getDate()).padStart(2, '0')}`;
}

export function formatDateTime(iso: string) {
  const d = parseServerDate(iso);
  return `${formatDate(iso)} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
}
