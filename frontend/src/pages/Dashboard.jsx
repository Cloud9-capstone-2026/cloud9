import { useState, useMemo } from 'react';
import { TrendingUp, TrendingDown, ArrowRight } from 'lucide-react';
import {
  ComposedChart, Bar, Line, XAxis, YAxis, Tooltip, CartesianGrid,
  ResponsiveContainer, PieChart, Pie, Cell,
} from 'recharts';

// ── 하드코딩 유지 항목 ────────────────────────────────────────────
const tendencies = [
  { label: '장기보유 성향',         level: '높음' },
  { label: '손절회피 성향',         level: '높음' },
  { label: '손절 직후 재진입 성향', level: '낮음' },
  { label: 'FOMO 성향',            level: '보통' },
  { label: '과잉확신 성향',         level: '높음' },
  { label: '분산투자 성향',         level: '보통' },
];

const pieData = [
  { name: '위험', value: 18,  pct: '19.1%', color: '#FF8A00' },
  { name: '주의', value: 22,  pct: '28.9%', color: '#FDE047' },
  { name: '양호', value: 210, pct: '52.0%', color: '#6EE7B7' },
];

const insights = [
  { color: '#FF8A00', text: '손절 회피가 12회로 가장 많이 탐지되었습니다.' },
  { color: '#FDE047', text: '이상 탐지 거래의 평균 손실은 일반 거래 대비 2.1배 높았습니다.' },
  { color: '#6EE7B7', text: '직전 분석 대비 FOMO 패턴이 2회 감소하였습니다.' },
];

// ── 색 헬퍼 ──────────────────────────────────────────────────────
const STATUS_COLOR = { 위험: '#FF8A00', 주의: '#FDE047', 양호: '#6EE7B7', '-': '#94A3B8' };
const LEVEL_COLOR  = { 높음: '#FF8A00', 보통: '#FDE047', 낮음: '#6EE7B7' };
const MONTH_LABEL  = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

function statusDot(status) {
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}>
      <span style={{ width: 7, height: 7, borderRadius: '50%', background: STATUS_COLOR[status] ?? '#94A3B8', display: 'inline-block' }} />
      <span style={{ color: STATUS_COLOR[status] ?? '#94A3B8', fontWeight: 500 }}>{status}</span>
    </span>
  );
}

// ── 요약 카드 ─────────────────────────────────────────────────────
function SummaryCard({ label, value, diff, diffType }) {
  const isUp  = diffType === 'up';
  const color = isUp ? '#F43F5E' : '#60A5FA';
  const Icon  = isUp ? TrendingUp : TrendingDown;
  return (
    <div style={s.card}>
      <p style={s.cardLabel}>{label}</p>
      <p style={s.cardValue}>{value}</p>
      <div style={s.cardDiffArea}>
        <p style={s.cardDiffSub}>지난 분석 대비</p>
        <div style={s.cardDiffRow}>
          {diffType
            ? <><span style={{ color, fontSize: 13, fontWeight: 600 }}>{diff}</span><Icon size={14} color={color} /></>
            : <span style={{ fontSize: 13, color: '#94A3B8' }}>{diff}</span>
          }
        </div>
      </div>
    </div>
  );
}

// ── 콤보 차트 커스텀 바 ───────────────────────────────────────────
function GradientBar({ x, y, width, height, opacity = 1 }) {
  const r = 6;
  const gradId = 'barGrad';
  const path = `M${x},${y + r} Q${x},${y} ${x + r},${y} H${x + width - r} Q${x + width},${y} ${x + width},${y + r} V${y + height} H${x} Z`;
  return (
    <g opacity={opacity}>
      <defs>
        <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%"   stopColor="#94A3B8" stopOpacity={1} />
          <stop offset="100%" stopColor="#94A3B8" stopOpacity={0} />
        </linearGradient>
      </defs>
      <path d={path} fill={`url(#${gradId})`} />
    </g>
  );
}

// ── 메인 컴포넌트 ──────────────────────────────────────────────────
export default function Dashboard({ onNavigate, trades = [], analysis = [] }) {
  const [activeTab, setActiveTab] = useState('trades');
  const barOpacity  = activeTab === 'trades'    ? 1 : 0.4;
  const lineOpacity = activeTab === 'anomalies' ? 1 : 0.4;

  // ── 요약 지표 계산 ────────────────────────────────────────────
  const totalTrades    = trades.length;
  const totalAnomalies = analysis.filter(a => a.is_anomaly).length;
  const anomalyRate    = totalTrades > 0 ? ((totalAnomalies / totalTrades) * 100).toFixed(1) : '0.0';
  const avgRiskScore   = analysis.length > 0
    ? Math.round(analysis.reduce((sum, a) => sum + (a.final_score || 0), 0) / analysis.length * 100)
    : 0;

  // ── 지난 분석 대비 ────────────────────────────────────────────
  // 트레이드: upload_id 기준 배치 구분
  const tradeUploadIds = useMemo(() =>
    [...new Set(trades.map(t => t.upload_id))].filter(v => v != null).sort((a, b) => b - a),
    [trades]
  );
  const curTrades  = tradeUploadIds.length > 0 ? trades.filter(t => t.upload_id === tradeUploadIds[0]) : trades;
  const prevTrades = tradeUploadIds.length > 1 ? trades.filter(t => t.upload_id === tradeUploadIds[1]) : [];

  // 분석 결과: upload_id 미저장이므로 analyzed_at 기준 5분 간격으로 배치 구분
  const analysisRuns = useMemo(() => {
    if (!analysis.length) return [];
    const sorted = [...analysis].sort((a, b) => new Date(b.analyzed_at) - new Date(a.analyzed_at));
    const groups = [];
    let group = [sorted[0]];
    for (let i = 1; i < sorted.length; i++) {
      const gap = new Date(sorted[i - 1].analyzed_at) - new Date(sorted[i].analyzed_at);
      if (gap < 5 * 60 * 1000) group.push(sorted[i]);
      else { groups.push(group); group = [sorted[i]]; }
    }
    groups.push(group);
    return groups;
  }, [analysis]);

  const curAnalysis  = analysisRuns[0] || [];
  const prevAnalysis = analysisRuns[1] || [];

  const makeDiff = (curVal, prevVal, hasPrevData, unit, decimals = 0) => {
    if (!hasPrevData) return { text: '-', type: null };
    const d = curVal - prevVal;
    const fmt = decimals > 0 ? Math.abs(d).toFixed(decimals) : Math.abs(Math.round(d));
    return { text: `${d >= 0 ? '+' : '-'}${fmt}${unit}`, type: d >= 0 ? 'up' : 'down' };
  };

  const cur = {
    trades:    curTrades.length,
    anomalies: curAnalysis.filter(a => a.is_anomaly).length,
    rate:      curAnalysis.length > 0 ? curAnalysis.filter(a => a.is_anomaly).length / curAnalysis.length * 100 : 0,
    risk:      curAnalysis.length > 0 ? Math.round(curAnalysis.reduce((s, a) => s + (a.final_score || 0), 0) / curAnalysis.length * 100) : 0,
  };
  const prev = {
    trades:    prevTrades.length,
    anomalies: prevAnalysis.filter(a => a.is_anomaly).length,
    rate:      prevAnalysis.length > 0 ? prevAnalysis.filter(a => a.is_anomaly).length / prevAnalysis.length * 100 : 0,
    risk:      prevAnalysis.length > 0 ? Math.round(prevAnalysis.reduce((s, a) => s + (a.final_score || 0), 0) / prevAnalysis.length * 100) : 0,
  };

  const diffs = {
    trades:    makeDiff(cur.trades,    prev.trades,    prevTrades.length > 0,   '회'),
    anomalies: makeDiff(cur.anomalies, prev.anomalies, prevAnalysis.length > 0, '건'),
    rate:      makeDiff(cur.rate,      prev.rate,      prevAnalysis.length > 0, '%', 1),
    risk:      makeDiff(cur.risk,      prev.risk,      prevAnalysis.length > 0, '점'),
  };

  // ── 월별 차트 데이터 ──────────────────────────────────────────
  const monthlyData = useMemo(() => {
    const map = {};
    trades.forEach(t => {
      const d = String(t.거래일자 || '').slice(0, 7);
      if (!d) return;
      if (!map[d]) map[d] = { key: d, trades: 0, anomalies: 0 };
      map[d].trades++;
    });
    analysis.forEach(a => {
      const d = String(a.xai_result?.날짜 || '').slice(0, 7);
      if (!d || !map[d]) return;
      if (a.is_anomaly) map[d].anomalies++;
    });
    return Object.values(map)
      .sort((a, b) => a.key.localeCompare(b.key))
      .slice(-6)
      .map(m => ({ month: MONTH_LABEL[parseInt(m.key.slice(5))] || m.key.slice(5), trades: m.trades, anomalies: m.anomalies }));
  }, [trades, analysis]);

  const chartData = monthlyData;

  // ── 최근 매매 내역 ────────────────────────────────────────────
  const recentTrades = useMemo(() => {
    if (!trades.length) return [];
    const aMap = {};
    analysis.forEach(a => {
      const key = `${a.xai_result?.종목명}_${a.xai_result?.날짜}`;
      if (!aMap[key]) aMap[key] = a;
    });
    return [...trades]
      .sort((a, b) => new Date(b.거래일자) - new Date(a.거래일자))
      .slice(0, 5)
      .map(t => {
        const dateStr = String(t.거래일자 || '');
        const matched = aMap[`${t.종목명}_${dateStr}`];
        return {
          name:   t.종목명,
          price:  `₩${Number(t.거래단가).toLocaleString()}`,
          status: matched ? (matched.is_anomaly ? '위험' : '양호') : '양호',
          date:   dateStr.replace(/-/g, '/'),
        };
      });
  }, [trades, analysis]);

  return (
    <div style={s.page}>
      {/* 요약 지표 */}
      <section>
        <p style={s.sectionHeading}>요약 지표</p>
        <div style={s.summaryRow}>
          <SummaryCard label="총 매매 횟수"      value={`${totalTrades}회`}   diff={diffs.trades.text}    diffType={diffs.trades.type} />
          <SummaryCard label="총 이상 탐지 건수"  value={`${totalAnomalies}건`} diff={diffs.anomalies.text} diffType={diffs.anomalies.type} />
          <SummaryCard label="이상 탐지율"        value={`${anomalyRate}%`}     diff={diffs.rate.text}      diffType={diffs.rate.type} />
          <SummaryCard label="평균 위험 점수"     value={`${avgRiskScore}점`}   diff={diffs.risk.text}      diffType={diffs.risk.type} />
        </div>
      </section>

      {/* 차트 + 성향 */}
      <section style={s.midRow}>
        <div style={{ ...s.card, flex: 1, minWidth: 604 }}>
          <div style={s.chartHeader}>
            <span style={s.chartMonthly}>월별</span>
            <TabBtn label="매매 횟수"     id="trades"    active={activeTab} onToggle={setActiveTab} />
            <span style={s.tabDivider}>│</span>
            <TabBtn label="이상 탐지 건수" id="anomalies" active={activeTab} onToggle={setActiveTab} />
          </div>
          <ResponsiveContainer width="100%" height={260}>
            <ComposedChart data={chartData} margin={{ top: 8, right: 16, left: -10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255,255,255,0.06)" />
              <XAxis dataKey="month" tick={{ fill: '#64748B', fontSize: 12 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: '#64748B', fontSize: 12 }} axisLine={false} tickLine={false} domain={['auto', 'auto']} />
              <Tooltip contentStyle={{ background: '#1E293B', border: 'none', borderRadius: 10, color: '#F8FAFC', fontSize: 12 }} cursor={{ fill: 'rgba(148,163,184,0.08)' }} />
              <Bar dataKey="trades" shape={(props) => <GradientBar {...props} opacity={barOpacity} />} maxBarSize={40} />
              <Line type="monotone" dataKey="anomalies" stroke="#FACC15" strokeWidth={2} strokeOpacity={lineOpacity}
                dot={(dotProps) => { const { cx, cy, key } = dotProps; return <circle key={key} cx={cx} cy={cy} r={4} fill="#FACC15" fillOpacity={lineOpacity} stroke="none" />; }}
                activeDot={{ r: 5, fill: '#FACC15' }}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>

        <div style={{ ...s.card, width: 260, flexShrink: 0, alignSelf: 'stretch', display: 'flex', flexDirection: 'column' }}>
          <p style={s.sectionTitle}>나의 성향 분석</p>
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'space-between', marginTop: 16 }}>
            {tendencies.map(({ label, level }) => {
              const col = LEVEL_COLOR[level];
              return (
                <div key={label} style={s.tendencyRow}>
                  <span style={s.tendencyLabel}>{label}</span>
                  <span style={{ ...s.levelBadge, color: col, background: col + '4D' }}>{level}</span>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* 하단 */}
      <section style={s.midRow}>
        <div style={{ ...s.card, flex: 1, minWidth: 524, alignSelf: 'stretch', display: 'flex', flexDirection: 'column' }}>
          <p style={s.sectionTitle}>최근 매매 내역</p>
          <table style={s.table}>
            <colgroup>
              <col style={{ width: '30%' }} /><col style={{ width: '30%' }} />
              <col style={{ width: '20%' }} /><col style={{ width: '20%' }} />
            </colgroup>
            <thead>
              <tr>{['종목명', '거래단가', '상태', '거래일자'].map(h => <th key={h} style={s.th}>{h}</th>)}</tr>
            </thead>
            <tbody>
              {recentTrades.map((row, i) => (
                <tr key={i} style={s.tr}>
                  <td style={s.td}>{row.name}</td>
                  <td style={s.td}>{row.price}</td>
                  <td style={s.td}>{statusDot(row.status)}</td>
                  <td style={s.td}>{row.date}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div style={{ flex: 1 }} />
          <button onClick={() => onNavigate('report')} style={s.linkBtn}>
            리포트에서 전체 보기 <ArrowRight size={14} style={{ marginLeft: 4 }} />
          </button>
        </div>

        <div style={{ ...s.card, width: 340, flexShrink: 0, alignSelf: 'stretch', display: 'flex', flexDirection: 'column' }}>
          <p style={s.sectionTitle}>매매 분석 요약</p>
          <div style={s.pieRow}>
            <div style={{ position: 'relative', display: 'inline-block', width: 120, height: 120, flexShrink: 0 }}>
              <PieChart width={120} height={120}>
                <Pie data={pieData} cx={60} cy={60} innerRadius={36} outerRadius={55} dataKey="value" strokeWidth={0} paddingAngle={5} cornerRadius={5} labelLine={false}>
                  {pieData.map((entry, index) => <Cell key={index} fill={entry.color} />)}
                </Pie>
              </PieChart>
              <div style={s.pieCenter}>
                <p style={s.pieCenterSub}>Total</p>
                <p style={s.pieCenterVal}>250</p>
              </div>
            </div>
            <div style={s.legend}>
              {pieData.map(({ name, value, pct, color }) => (
                <div key={name} style={s.legendRow}>
                  <span style={{ width: 8, height: 8, borderRadius: '50%', background: color }} />
                  <span style={{ color: '#F8FAFC', fontSize: 13 }}>{name}</span>
                  <span style={{ color: '#F8FAFC', fontSize: 13, fontWeight: 600, textAlign: 'right' }}>{value}</span>
                  <span style={{ color: '#64748B', fontSize: 12, textAlign: 'right' }}>{pct}</span>
                </div>
              ))}
            </div>
          </div>
          <div style={s.insightDivider} />
          <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between', flex: 1 }}>
            {insights.map(({ color, text }, i) => (
              <div key={i} style={s.insightRow}>
                <span style={{ width: 7, height: 7, borderRadius: '50%', background: color, flexShrink: 0, marginTop: 3 }} />
                <span style={{ color: '#F8FAFC', fontSize: 12, lineHeight: 1.5 }}>{text}</span>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}

function TabBtn({ label, id, active, onToggle }) {
  const isActive = active === id;
  return (
    <button onClick={() => onToggle(id)} style={{ background: 'none', border: 'none', fontFamily: 'Inter, sans-serif', fontSize: 14, fontWeight: isActive ? 600 : 400, color: '#F8FAFC', opacity: isActive ? 1 : 0.4, cursor: 'pointer', padding: '2px 0' }}>
      {label}
    </button>
  );
}

// ── 스타일 ────────────────────────────────────────────────────────
const s = {
  page:         { padding: '40px', display: 'flex', flexDirection: 'column', gap: 32 },
  sectionHeading: { fontSize: 15, fontWeight: 600, color: '#F8FAFC', marginBottom: 14 },
  summaryRow:   { display: 'grid', gridTemplateColumns: 'repeat(4, minmax(200px, 1fr))', gap: 32 },
  midRow:       { display: 'flex', gap: 32, alignItems: 'flex-start' },
  card:         { background: '#1E293B', borderRadius: 16, padding: '20px 22px' },
  cardLabel:    { fontSize: 13, color: '#F8FAFC', marginBottom: 8 },
  cardValue:    { fontSize: 30, fontWeight: 700, color: '#F8FAFC', marginBottom: 12 },
  cardDiffArea: { display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 2 },
  cardDiffSub:  { fontSize: 11, color: '#94A3B8' },
  cardDiffRow:  { display: 'flex', alignItems: 'center', gap: 3 },
  chartHeader:  { display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 },
  chartMonthly: { fontSize: 14, fontWeight: 600, color: '#F8FAFC' },
  tabDivider:   { color: '#334155', fontSize: 16 },
  sectionTitle: { fontSize: 14, fontWeight: 600, color: '#F8FAFC' },
  tendencyRow:  { display: 'flex', justifyContent: 'space-between', alignItems: 'center' },
  tendencyLabel:{ fontSize: 13, color: '#F8FAFC' },
  levelBadge:   { fontSize: 11, fontWeight: 600, padding: '3px 10px', borderRadius: 999 },
  table:        { width: '100%', borderCollapse: 'collapse', marginTop: 16 },
  th:           { fontSize: 12, color: '#64748B', fontWeight: 500, textAlign: 'left', paddingBottom: 10, borderBottom: '1px solid #334155' },
  tr:           { borderBottom: '1px solid rgba(51,65,85,0.5)' },
  td:           { fontSize: 13, color: '#F8FAFC', padding: '12px 0' },
  linkBtn:      { display: 'flex', alignItems: 'center', justifyContent: 'center', width: '100%', marginTop: 14, paddingTop: 14, borderTop: '1px solid #334155', background: 'none', border: 'none', color: '#94A3B8', fontSize: 13, cursor: 'pointer', fontFamily: 'Inter, sans-serif' },
  pieRow:       { display: 'flex', flexDirection: 'row', alignItems: 'center', justifyContent: 'flex-start', gap: 24, marginTop: 12 },
  pieCenter:    { position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', textAlign: 'center', whiteSpace: 'nowrap', pointerEvents: 'none' },
  pieCenterSub: { fontSize: 11, color: '#94A3B8', marginBottom: 2 },
  pieCenterVal: { fontSize: 22, fontWeight: 700, color: '#F8FAFC' },
  legend:       { display: 'flex', flexDirection: 'column', gap: 10 },
  legendRow:    { display: 'grid', gridTemplateColumns: '16px 40px 30px 44px', alignItems: 'center', gap: 6 },
  insightDivider: { height: 1, background: '#334155', margin: '14px 0' },
  insightRow:   { display: 'flex', alignItems: 'flex-start', gap: 8 },
};
