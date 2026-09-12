import { RISK, biasColorOf, BIAS_KEYS, BIAS_KEY_MAP } from '../theme/tokens';
import { formatDate } from '../utils/formatDate';
import { verdictToRisk } from '../utils/matchTradeAnalysis';
import type { TradeRaw } from '../api/trades';
import type { AnalysisResult, AnalysisEvidenceFeature } from '../api/analysis';

const DEV_SEGS = [
  { max: 1, label: '평소와 비슷해요' },
  { max: 2, label: '평소와 조금 달라요' },
  { max: 3, label: '평소와 달라요' },
  { max: Infinity, label: '평소보다 많이 달라요' },
];

// evidence의 attribution(로짓, 내부 단위)은 화면에 숫자로 노출하지 않고 순위·방향만 쓴다 —
// 서버가 실제로 돌려준 feature만 랭킹하고, 없는 걸 지어내지 않는다.
function rankedFeatures(features: AnalysisEvidenceFeature[]) {
  return [...features]
    .sort((a, b) => Math.abs(b.attribution) - Math.abs(a.attribution))
    .map((f, i) => ({
      rank: i + 1,
      name: f.feature,
      dir: f.attribution > 0 ? '▲ 편향 강화' : '▼ 편향 약화',
      dirColor: f.attribution > 0 ? '#DC2626' : '#0066FF',
    }));
}

interface RankedFeature {
  rank: number;
  name: string;
  dir: string;
  dirColor: string;
}

interface BiasRow {
  key: string;
  name: string;
  score: number;
  isTop: boolean;
  color: string;
}

interface EvidenceRow {
  key: string;
  name: string;
  color: string;
  isTop: boolean;
  tradePct: number;
  tradeLabel: string;
  contextLabel: string;
  ranked: RankedFeature[];
}

interface ReportDetailVM {
  stock: string;
  analyzedAt: string | null;
  rows: { k: string; v: string }[];
  layerSummary: string;
  verdict: string;
  verdictColor: string;
  layers: { label: string; score: number; triggered: boolean; failed: boolean }[];
  lstmFailed: boolean;
  rules: string[];
  hasDeviation: boolean;
  devLabel: string;
  sigmaText: string;
  markerPct: number;
  markerColor: string;
  activeSeg: number;
  showBias: boolean;
  biasRows: BiasRow[];
  showEvidence: boolean;
  evidence: EvidenceRow[];
}

function tradeRows(trade: TradeRaw) {
  return [
    { k: '거래구분', v: trade.거래구분 },
    { k: '거래일자', v: formatDate(trade.거래일자) },
    { k: '거래단가', v: `${trade.거래단가.toLocaleString()}원` },
    { k: '수량', v: `${trade.거래수량}주` },
    { k: '거래금액', v: `${trade.거래금액.toLocaleString()}원` },
    { k: '실거래금액(정산)', v: `${trade.정산금액.toLocaleString()}원` },
  ];
}

export function buildReportDetailVM(trade: TradeRaw, ana: AnalysisResult | null): ReportDetailVM {
  // 매칭되는 분석 결과가 없는 경우(분석 전이거나, upload_id+날짜+종목명 매칭이 안 된 드문 케이스) —
  // 거래 정보는 보여주되 분석 관련 섹션은 전부 숨긴다.
  if (!ana) {
    return {
      stock: trade.종목명,
      analyzedAt: null as string | null,
      rows: tradeRows(trade),
      layerSummary: '분석 결과가 아직 없어요',
      verdict: '-',
      verdictColor: RISK.safe.color,
      layers: [
        { label: '규칙 기반', score: 0, triggered: false, failed: true },
        { label: '통계 분석', score: 0, triggered: false, failed: true },
        { label: '딥러닝', score: 0, triggered: false, failed: true },
      ],
      lstmFailed: true,
      rules: ['없음'],
      hasDeviation: false,
      devLabel: '',
      sigmaText: '',
      markerPct: 0,
      markerColor: '#9CA3AF',
      activeSeg: 0,
      showBias: false,
      biasRows: [],
      showEvidence: false,
      evidence: [],
    };
  }

  const xai = ana.detail;
  const verdictRisk = verdictToRisk(xai.verdict);
  const lstmFailed = ana.deep_score == null;
  const hasDeviation = xai.mahalanobis != null;

  let activeSeg = 0;
  if (hasDeviation) {
    activeSeg = DEV_SEGS.findIndex((x) => (xai.mahalanobis as number) < x.max);
    if (activeSeg < 0) activeSeg = 3;
  }

  const showBias = !lstmFailed && !!xai.bias_scores;
  const showEvidence = !lstmFailed && !!xai.evidence;

  return {
    stock: trade.종목명,
    analyzedAt: formatDate(ana.analyzed_at),
    rows: tradeRows(trade),
    layerSummary: `${xai.layers_available}개 계층 중 ${[xai.flags.rule, xai.flags.stat, xai.flags.deep].filter(Boolean).length}개 탐지`,
    verdict: xai.verdict,
    verdictColor: RISK[verdictRisk].color,
    layers: [
      { label: '규칙 기반', score: Math.round((ana.rule_score ?? 0) * 100), triggered: !!xai.flags.rule, failed: ana.rule_score == null },
      { label: '통계 분석', score: Math.round((ana.stat_score ?? 0) * 100), triggered: !!xai.flags.stat, failed: ana.stat_score == null },
      { label: '딥러닝', score: ana.deep_score != null ? Math.round(ana.deep_score * 100) : 0, triggered: !!xai.flags.deep, failed: lstmFailed },
    ],
    lstmFailed,
    rules: xai.triggered_rules && xai.triggered_rules.length ? xai.triggered_rules.map((r) => `#${r}`) : ['없음'],
    hasDeviation,
    devLabel: hasDeviation ? DEV_SEGS[activeSeg].label : '측정할 수 없어요',
    sigmaText: hasDeviation ? `${xai.mahalanobis}σ` : '-',
    markerPct: hasDeviation ? Math.min((xai.mahalanobis as number) / 4, 0.97) * 100 : 0,
    markerColor: activeSeg === 0 ? '#9CA3AF' : '#EF4444',
    activeSeg,
    showBias,
    biasRows: showBias
      ? BIAS_KEYS.map((k) => {
          const score = Math.round((xai.bias_scores![k] || 0) * 100);
          const isTop = k === xai.top_bias;
          return { key: k, name: BIAS_KEY_MAP[k], score, isTop, color: biasColorOf(k) };
        })
      : [],
    showEvidence,
    evidence: showEvidence
      ? BIAS_KEYS.map((k) => {
          const ev = xai.evidence![k];
          return {
            key: k,
            name: BIAS_KEY_MAP[k],
            color: biasColorOf(k),
            isTop: k === xai.top_bias,
            tradePct: ev.trade_share * 100,
            tradeLabel: `${Math.round(ev.trade_share * 100)}%`,
            contextLabel: `${Math.round(ev.context_share * 100)}%`,
            ranked: rankedFeatures(ev.features),
          };
        })
      : [],
  };
}
