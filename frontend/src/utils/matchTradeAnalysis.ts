import type { TradeRaw } from '../api/trades';
import type { AnalysisResult } from '../api/analysis';
import type { RiskLevel } from '../theme/tokens';

// AnalysisResult에는 거래 고유 id로의 연결이 없다(백엔드 orm.AnalysisResult에 trade_id
// 컬럼 자체가 없음) — upload_id + 날짜 + 종목명 조합으로만 대조 가능하다. 같은 업로드에서
// 같은 날 같은 종목을 두 번 이상 거래했으면(분할 매수 등) 그중 하나에만 매칭될 수 있는
// 서버 쪽 한계 — 프론트에서 더 정교하게 고칠 방법이 없다.
function matchKey(uploadId: number | null, dateIso: string, stock: string) {
  return `${uploadId ?? 'null'}|${dateIso.slice(0, 10)}|${stock}`;
}

export function verdictToRisk(verdict: '정상' | '경고' | '이상'): RiskLevel {
  return verdict === '이상' ? 'danger' : verdict === '경고' ? 'caution' : 'safe';
}

export function buildAnalysisLookup(analysis: AnalysisResult[]): Map<string, AnalysisResult> {
  const map = new Map<string, AnalysisResult>();
  analysis.forEach((a) => {
    map.set(matchKey(a.upload_id, a.detail.날짜, a.detail.종목명), a);
  });
  return map;
}

export function findAnalysisForTrade(
  lookup: Map<string, AnalysisResult>,
  trade: TradeRaw
): AnalysisResult | null {
  return lookup.get(matchKey(trade.upload_id, trade.거래일자, trade.종목명)) ?? null;
}
