import { useState } from 'react';
import { TrendingUp, TrendingDown, ArrowRight } from 'lucide-react';
import {
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts';

// ── 샘플 데이터 ──────────────────────────────────────────────
const monthlyData = [
  { month: 'Jan', trades: 28, anomalies: 3 },
  { month: 'Feb', trades: 42, anomalies: 5 },
  { month: 'Mar', trades: 35, anomalies: 4 },
  { month: 'Apr', trades: 18, anomalies: 8 },
  { month: 'May', trades: 38, anomalies: 2 },
  { month: 'Jun', trades: 52, anomalies: 6 },
  { month: 'Jul', trades: 37, anomalies: 4 },
];

const recentTrades = [
  { name: '삼성전자',       price: '₩266,500',   status: '위험', date: '2026/05/20' },
  { name: '현대차',         price: '₩592,000',   status: '양호', date: '2026/05/20' },
  { name: 'SK하이닉스',     price: '₩1,976,000', status: '위험', date: '2026/05/13' },
  { name: '삼성전자',       price: '₩230,000',   status: '주의', date: '2026/05/02' },
  { name: 'LG에너지솔루션', price: '₩472,000',   status: '양호', date: '2026/04/28' },
];

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

// ── 색 헬퍼 ──────────────────────────────────────────────────
const STATUS_COLOR = { 위험: '#FF8A00', 주의: '#FDE047', 양호: '#6EE7B7' };
const LEVEL_COLOR  = { 높음: '#FF8A00', 보통: '#FDE047', 낮음: '#6EE7B7' };

function statusDot(status) {
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}>
      <span style={{ width: 7, height: 7, borderRadius: '50%', background: STATUS_COLOR[status], display: 'inline-block' }} />
      <span style={{ color: STATUS_COLOR[status], fontWeight: 500 }}>{status}</span>
    </span>
  );
}

// ── 요약 카드 ─────────────────────────────────────────────────
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
          <span style={{ color, fontSize: 13, fontWeight: 600 }}>{diff}</span>
          <Icon size={14} color={color} />
        </div>
      </div>
    </div>
  );
}

// ── 콤보 차트 커스텀 바 ───────────────────────────────────────
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

// ── 메인 컴포넌트 ──────────────────────────────────────────────
export default function Dashboard({ onNavigate }) {
  const [activeTab, setActiveTab] = useState('trades');
  const barOpacity  = activeTab === 'trades'    ? 1 : 0.4;
  const lineOpacity = activeTab === 'anomalies' ? 1 : 0.4;

  return (
    <div style={s.page}>
      {/* 요약 지표 */}
      <section>
        <p style={s.sectionHeading}>요약 지표</p>
        <div style={s.summaryRow}>
          <SummaryCard label="총 매매 횟수"      value="250회" diff="+50회"  diffType="up" />
          <SummaryCard label="총 이상 탐지 건수"  value="20건"  diff="+3건"   diffType="up" />
          <SummaryCard label="이상 탐지율"        value="11.1%" diff="-0.03%" diffType="down" />
          <SummaryCard label="평균 위험 점수"     value="61점"  diff="-5점"   diffType="down" />
        </div>
      </section>

      {/* 차트 + 성향 */}
      <section style={s.midRow}>
        {/* 콤보 차트 */}
        <div style={{ ...s.card, flex: 1, minWidth: 604 }}>
          <div style={s.chartHeader}>
            <span style={s.chartMonthly}>월별</span>
            <TabBtn label="매매 횟수"     id="trades"    active={activeTab} onToggle={setActiveTab} />
            <span style={s.tabDivider}>│</span>
            <TabBtn label="이상 탐지 건수" id="anomalies" active={activeTab} onToggle={setActiveTab} />
          </div>
          <ResponsiveContainer width="100%" height={260}>
            <ComposedChart data={monthlyData} margin={{ top: 8, right: 16, left: -10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255,255,255,0.06)" />
              <XAxis
                dataKey="month"
                tick={{ fill: '#64748B', fontSize: 12 }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                tick={{ fill: '#64748B', fontSize: 12 }}
                axisLine={false}
                tickLine={false}
                domain={['auto', 'auto']}
              />
              <Tooltip
                contentStyle={{ background: '#1E293B', border: 'none', borderRadius: 10, color: '#F8FAFC', fontSize: 12 }}
                cursor={{ fill: 'rgba(148,163,184,0.08)' }}
              />
              <Bar
                dataKey="trades"
                shape={(props) => <GradientBar {...props} opacity={barOpacity} />}
                maxBarSize={40}
              />
              <Line
                type="monotone"
                dataKey="anomalies"
                stroke="#FACC15"
                strokeWidth={2}
                strokeOpacity={lineOpacity}
                dot={(dotProps) => {
                  const { cx, cy, key } = dotProps;
                  return (
                    <circle
                      key={key}
                      cx={cx}
                      cy={cy}
                      r={4}
                      fill="#FACC15"
                      fillOpacity={lineOpacity}
                      stroke="none"
                    />
                  );
                }}
                activeDot={{ r: 5, fill: '#FACC15' }}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>

        {/* 성향 분석 */}
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
        {/* 최근 매매 내역 */}
        <div style={{ ...s.card, flex: 1, minWidth: 524, alignSelf: 'stretch', display: 'flex', flexDirection: 'column' }}>
          <p style={s.sectionTitle}>최근 매매 내역</p>
          <table style={s.table}>
            <colgroup>
              <col style={{ width: '30%' }} />
              <col style={{ width: '30%' }} />
              <col style={{ width: '20%' }} />
              <col style={{ width: '20%' }} />
            </colgroup>
            <thead>
              <tr>
                {['종목명', '거래단가', '상태', '거래일자'].map(h => (
                  <th key={h} style={s.th}>{h}</th>
                ))}
              </tr>
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

        {/* 매매 분석 요약 */}
        <div style={{ ...s.card, width: 340, flexShrink: 0, alignSelf: 'stretch', display: 'flex', flexDirection: 'column' }}>
          <p style={s.sectionTitle}>매매 분석 요약</p>
          <div style={s.pieRow}>
            {/* 링차트 + 오버레이 텍스트 */}
            <div style={{ position: 'relative', display: 'inline-block', width: 120, height: 120, flexShrink: 0 }}>
              <PieChart width={120} height={120}>
                <Pie
                  data={pieData}
                  cx={60}
                  cy={60}
                  innerRadius={36}
                  outerRadius={55}
                  dataKey="value"
                  strokeWidth={0}
                  paddingAngle={5}
                  cornerRadius={5}
                  labelLine={false}
                >
                  {pieData.map((entry, index) => (
                    <Cell key={index} fill={entry.color} />
                  ))}
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
          <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between', flex: 1}}>
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
    <button
      onClick={() => onToggle(id)}
      style={{
        background: 'none',
        border: 'none',
        fontFamily: 'Inter, sans-serif',
        fontSize: 14,
        fontWeight: isActive ? 600 : 400,
        color: '#F8FAFC',
        opacity: isActive ? 1 : 0.4,
        cursor: 'pointer',
        padding: '2px 0',
      }}
    >
      {label}
    </button>
  );
}

// ── 스타일 ────────────────────────────────────────────────────
const s = {
  page: {
    padding: '40px',
    display: 'flex',
    flexDirection: 'column',
    gap: 32,
  },
  sectionHeading: {
    fontSize: 15,
    fontWeight: 600,
    color: '#F8FAFC',
    marginBottom: 14,
  },
  summaryRow: {
    display: 'grid',
    gridTemplateColumns: 'repeat(4, minmax(200px, 1fr))',
    gap: 32,
  },
  midRow: {
    display: 'flex',
    gap: 32,
    alignItems: 'flex-start',
  },
  card: {
    background: '#1E293B',
    borderRadius: 16,
    padding: '20px 22px',
  },
  cardLabel: {
    fontSize: 13,
    color: '#F8FAFC',
    marginBottom: 8,
  },
  cardValue: {
    fontSize: 30,
    fontWeight: 700,
    color: '#F8FAFC',
    marginBottom: 12,
  },
  cardDiffArea: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'flex-end',
    gap: 2,
  },
  cardDiffSub: {
    fontSize: 11,
    color: '#94A3B8',
  },
  cardDiffRow: {
    display: 'flex',
    alignItems: 'center',
    gap: 3,
  },
  chartHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
    marginBottom: 8,
  },
  chartMonthly: {
    fontSize: 14,
    fontWeight: 600,
    color: '#F8FAFC',
  },
  tabDivider: {
    color: '#334155',
    fontSize: 16,
  },
  sectionTitle: {
    fontSize: 14,
    fontWeight: 600,
    color: '#F8FAFC',
  },
  tendencyRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  tendencyLabel: {
    fontSize: 13,
    color: '#F8FAFC',
  },
  levelBadge: {
    fontSize: 11,
    fontWeight: 600,
    padding: '3px 10px',
    borderRadius: 999,
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    marginTop: 16,
  },
  th: {
    fontSize: 12,
    color: '#64748B',
    fontWeight: 500,
    textAlign: 'left',
    paddingBottom: 10,
    borderBottom: '1px solid #334155',
  },
  tr: {
    borderBottom: '1px solid rgba(51,65,85,0.5)',
  },
  td: {
    fontSize: 13,
    color: '#F8FAFC',
    padding: '12px 0',
  },
  linkBtn: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: '100%',
    marginTop: 14,
    paddingTop: 14,
    borderTop: '1px solid #334155',
    background: 'none',
    border: 'none',
    borderTop: '1px solid #334155',
    color: '#94A3B8',
    fontSize: 13,
    cursor: 'pointer',
    fontFamily: 'Inter, sans-serif',
  },
  pieRow: {
    display: 'flex',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'flex-start',
    gap: 24,
    marginTop: 12,
  },
  pieCenter: {
    position: 'absolute',
    top: '50%',
    left: '50%',
    transform: 'translate(-50%, -50%)',
    textAlign: 'center',
    whiteSpace: 'nowrap',
    pointerEvents: 'none',
  },
  pieCenterSub: {
    fontSize: 11,
    color: '#94A3B8',
    marginBottom: 2,
  },
  pieCenterVal: {
    fontSize: 22,
    fontWeight: 700,
    color: '#F8FAFC',
  },
  legend: {
    display: 'flex',
    flexDirection: 'column',
    gap: 10,
  },
  legendRow: {
    display: 'grid',
    gridTemplateColumns: '16px 40px 30px 44px',
    alignItems: 'center',
    gap: 6,
  },
  insightDivider: {
    height: 1,
    background: '#334155',
    margin: '14px 0',
  },
  insightRow: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: 8,
  
  },
};
