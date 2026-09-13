import type { TradeRaw } from '../api/trades';
import type { AnalysisResult } from '../api/analysis';
import type { RiskLevel } from '../theme/tokens';

// AnalysisResult.trade_id(2026-09-10 백엔드에 추가)로 거래 1건과 분석 결과 1건을 정확히
// 1:1 매칭한다. 이 컬럼 도입 이전에 만들어진 행은 trade_id가 null일 수 있어서, 그 경우에만
// 예전 방식(upload_id + 날짜 + 종목명)으로 대신 대조하는 폴백을 둔다 — 이 폴백은 같은 날
// 같은 종목을 두 번 이상 거래했으면 매칭이 애매할 수 있는 한계가 여전히 있지만, trade_id가
// 채워진 이후의 데이터는 이 문제 자체가 없다.
function legacyKey(uploadId: number | null, dateIso: string, stock: string) {
  return `${uploadId ?? 'null'}|${dateIso.slice(0, 10)}|${stock}`;
}

export function verdictToRisk(verdict: '정상' | '경고' | '이상'): RiskLevel {
  return verdict === '이상' ? 'danger' : verdict === '경고' ? 'caution' : 'safe';
}

export interface AnalysisLookup {
  byTradeId: Map<number, AnalysisResult>;
  byLegacyKey: Map<string, AnalysisResult>;
}

export function buildAnalysisLookup(analysis: AnalysisResult[]): AnalysisLookup {
  const byTradeId = new Map<number, AnalysisResult>();
  const byLegacyKey = new Map<string, AnalysisResult>();
  analysis.forEach((a) => {
    if (a.trade_id != null) {
      byTradeId.set(a.trade_id, a);
    } else {
      byLegacyKey.set(legacyKey(a.upload_id, a.detail.날짜, a.detail.종목명), a);
    }
  });
  return { byTradeId, byLegacyKey };
}

export function findAnalysisForTrade(
  lookup: AnalysisLookup,
  trade: TradeRaw
): AnalysisResult | null {
  return (
    lookup.byTradeId.get(trade.id) ??
    lookup.byLegacyKey.get(legacyKey(trade.upload_id, trade.거래일자, trade.종목명)) ??
    null
  );
}
