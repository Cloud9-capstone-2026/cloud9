// 한글 마지막 글자에 받침이 있는지 — 조사 선택(이/가, 은/는)의 기준.
export function hasBatchim(word: string): boolean {
  const last = word.charCodeAt(word.length - 1);
  return last >= 0xac00 && last <= 0xd7a3 && (last - 0xac00) % 28 !== 0;
}

// 받침 유무에 따라 "은"/"는" 보조사를 붙인다(예: "과잉확신" → "과잉확신은", "처분효과" → "처분효과는").
export function withTopicParticle(word: string): string {
  return `${word}${hasBatchim(word) ? '은' : '는'}`;
}
