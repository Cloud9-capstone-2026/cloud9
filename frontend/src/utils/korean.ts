// 받침 유무에 따라 "이"/"가" 주격조사를 붙인다(예: "과잉확신" → "과잉확신이", "처분효과" → "처분효과가").
export function withSubjectParticle(word: string): string {
  const last = word.charCodeAt(word.length - 1);
  const hasBatchim = last >= 0xac00 && last <= 0xd7a3 && (last - 0xac00) % 28 !== 0;
  return `${word}${hasBatchim ? '이' : '가'}`;
}
