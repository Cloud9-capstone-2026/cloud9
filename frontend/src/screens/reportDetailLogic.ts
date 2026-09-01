import { RISK, biasColorOf, BIAS_KEYS, BIAS_KEY_MAP, FEATURE_POOL, BiasKey } from '../theme/tokens';
import { tradesRaw, analysisData } from '../data/mock';
import type { EvidenceFeature } from '../data/types';

function seed(s: string): number {
  let x = 7;
  for (let i = 0; i < s.length; i++) x = (x * 31 + s.charCodeAt(i)) % 9973;
  return x;
}

export function rankedFeatures(biasKey: string, features: EvidenceFeature[]) {
  const map: Record<string, number> = {};
  features.forEach((f) => { map[f.feature] = f.attribution; });
  const all = FEATURE_POOL.map((name) => {
    let a = map[name];
    if (a === undefined) {
      const s2 = seed(biasKey + name);
      a = ((s2 % 350) / 100) * (s2 % 2 ? 1 : -1);
    }
    return { name, a };
  });
  all.sort((p, q) => Math.abs(q.a) - Math.abs(p.a));
  return all.map((f, i) => ({
    rank: i + 1,
    name: f.name,
    dir: f.a > 0 ? '▲ 편향 강화' : '▼ 편향 약화',
    dirColor: f.a > 0 ? '#DC2626' : '#0066FF',
  }));
}

// 탐지 규칙 설정(§5.2)의 7종 명칭과 표시를 일치시키기 위한 매핑.
// analysisData의 triggered_rules에는 규칙 개편 이전의 구 명칭이 섞여 있어 변환한다.
const RULE_NAME_MAP: Record<string, string> = {
  일중_반복매매: '일중_반복매매',
  당일_왕복매매: '당일_왕복매매',
  최소_보유기간: '최소_보유기간',
  손실_후_재진입: '손실_후_재진입',
  물타기_반복: '물타기_반복',
  '1회_매수금액_상한': '1회_매수금액_상한',
  일일_매매대금_상한: '일일_매매대금_상한',
  집중매매: '일일_매매대금_상한',
  반복매수: '물타기_반복',
};

function canonicalRules(raw: string[]): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  raw.forEach((r) => {
    const name = RULE_NAME_MAP[r] || r;
    if (!seen.has(name)) { seen.add(name); out.push(name); }
  });
  return out;
}

const DEV_SEGS = [
  { max: 1, label: '평소와 비슷해요' },
  { max: 2, label: '평소와 조금 달라요' },
  { max: 3, label: '평소와 달라요' },
  { max: Infinity, label: '평소보다 많이 달라요' },
];

export function buildReportDetailVM(tradeId: number) {
  const trade = tradesRaw.find((x) => x.id === tradeId) || tradesRaw[0];
  const ana = analysisData[tradeId] || analysisData[1];
  const xai = ana.xai_result;
  const verdictRisk = xai.verdict === '이상' ? 'danger' : xai.verdict === '경고' ? 'caution' : 'safe';
  const lstmFailed = ana.lstm_score === null;

  const layerDefs = [
    { label: '규칙 기반', score: Math.round(ana.rule_score * 100), triggered: xai.flags.rule, failed: false },
    { label: '통계 분석', score: Math.round(ana.stat_score * 100), triggered: xai.flags.stat, failed: false },
    { label: '딥러닝', score: ana.lstm_score !== null ? Math.round(ana.lstm_score * 100) : 0, triggered: !!xai.flags.deep, failed: lstmFailed },
  ];

  const sigma = xai.mahalanobis;
  let activeSeg = DEV_SEGS.findIndex((x) => sigma < x.max);
  if (activeSeg < 0) activeSeg = 3;

  const showEvidence = !lstmFailed && !!xai.evidence;
  const priceNum = Number(trade.price.replace(/,/g, ''));
  const computedAmount = priceNum * trade.qty;

  return {
    stock: trade.stock,
    rows: [
      { k: '거래구분', v: trade.type === 'buy' ? '매수' : '매도' },
      { k: '거래일자', v: trade.date },
      { k: '거래단가', v: `${trade.price}원` },
      { k: '수량', v: `${trade.qty}주` },
      { k: '거래금액', v: computedAmount ? `${computedAmount.toLocaleString()}원` : '-' },
      { k: '실거래금액', v: `${trade.amount}원` },
    ],
    layerSummary: `${xai.layers_available}개 계층 중 ${layerDefs.filter((l) => l.triggered).length}개 탐지`,
    verdict: xai.verdict,
    verdictColor: RISK[verdictRisk].color,
    layers: layerDefs,
    lstmFailed,
    rules: xai.triggered_rules.length ? canonicalRules(xai.triggered_rules).map((r) => `#${r}`) : ['없음'],
    devLabel: DEV_SEGS[activeSeg].label,
    sigmaText: `${sigma}σ`,
    markerPct: Math.min(sigma / 4, 0.97) * 100,
    markerColor: activeSeg === 0 ? '#9CA3AF' : '#EF4444',
    activeSeg,
    showBias: !lstmFailed,
    biasRows: BIAS_KEYS.map((k) => {
      const score = Math.round((xai.bias_scores[k] || 0) * 100);
      const isTop = k === xai.top_bias;
      return { key: k, name: BIAS_KEY_MAP[k], score, isTop, color: biasColorOf(k) };
    }),
    showEvidence,
    evidence: showEvidence
      ? BIAS_KEYS.map((k: BiasKey) => {
          const ev = xai.evidence![k];
          return {
            key: k,
            name: BIAS_KEY_MAP[k],
            color: biasColorOf(k),
            isTop: k === xai.top_bias,
            tradePct: ev.trade_share * 100,
            tradeLabel: `${Math.round(ev.trade_share * 100)}%`,
            contextLabel: `${Math.round(ev.context_share * 100)}%`,
            ranked: rankedFeatures(k, ev.features),
          };
        })
      : [],
  };
}
