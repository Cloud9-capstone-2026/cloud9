import { useState, useMemo } from 'react';
import { ArrowUpDown, Search, X, ChevronLeft, ChevronRight } from 'lucide-react';

const SAMPLE_DATA = [
  { id:1,  거래일자:"2026-06-30", 종목명:"삼성전자",        거래구분:"매수", 수량:10, 거래단가:66800,  거래금액:668000,  수수료:334, 거래세:201, 실거래금액:667465, 상태:"위험" },
  { id:2,  거래일자:"2026-06-29", 종목명:"SK하이닉스",      거래구분:"매도", 수량:5,  거래단가:178000, 거래금액:890000,  수수료:445, 거래세:267, 실거래금액:889288, 상태:"양호" },
  { id:3,  거래일자:"2026-06-28", 종목명:"NAVER",           거래구분:"매수", 수량:3,  거래단가:204500, 거래금액:613500,  수수료:307, 거래세:184, 실거래금액:613009, 상태:"경고" },
  { id:4,  거래일자:"2026-06-27", 종목명:"카카오",           거래구분:"매도", 수량:20, 거래단가:51200,  거래금액:1024000, 수수료:512, 거래세:307, 실거래금액:1023181,상태:"양호" },
  { id:5,  거래일자:"2026-06-26", 종목명:"현대차",           거래구분:"매수", 수량:2,  거래단가:234000, 거래금액:468000,  수수료:234, 거래세:140, 실거래금액:467626, 상태:"위험" },
  { id:6,  거래일자:"2026-06-25", 종목명:"LG에너지솔루션",   거래구분:"매수", 수량:1,  거래단가:412000, 거래금액:412000,  수수료:206, 거래세:124, 실거래금액:411670, 상태:"경고" },
  { id:7,  거래일자:"2026-06-24", 종목명:"삼성전자",         거래구분:"매도", 수량:10, 거래단가:68200,  거래금액:682000,  수수료:341, 거래세:205, 실거래금액:681454, 상태:"위험" },
  { id:8,  거래일자:"2026-06-23", 종목명:"셀트리온",         거래구분:"매수", 수량:4,  거래단가:178500, 거래금액:714000,  수수료:357, 거래세:214, 실거래금액:713429, 상태:"양호" },
  { id:9,  거래일자:"2026-06-22", 종목명:"기아",             거래구분:"매도", 수량:8,  거래단가:98400,  거래금액:787200,  수수료:394, 거래세:236, 실거래금액:786570, 상태:"양호" },
  { id:10, 거래일자:"2026-06-21", 종목명:"POSCO홀딩스",      거래구분:"매수", 수량:3,  거래단가:312000, 거래금액:936000,  수수료:468, 거래세:281, 실거래금액:935251, 상태:"경고" },
  { id:11, 거래일자:"2026-06-20", 종목명:"카카오",           거래구분:"매수", 수량:15, 거래단가:50800,  거래금액:762000,  수수료:381, 거래세:229, 실거래금액:761390, 상태:"위험" },
  { id:12, 거래일자:"2026-06-19", 종목명:"SK하이닉스",       거래구분:"매수", 수량:3,  거래단가:175000, 거래금액:525000,  수수료:263, 거래세:158, 실거래금액:524579, 상태:"양호" },
  { id:13, 거래일자:"2026-06-18", 종목명:"NAVER",            거래구분:"매도", 수량:2,  거래단가:208000, 거래금액:416000,  수수료:208, 거래세:125, 실거래금액:415667, 상태:"경고" },
  { id:14, 거래일자:"2026-06-17", 종목명:"삼성바이오로직스", 거래구분:"매수", 수량:1,  거래단가:856000, 거래금액:856000,  수수료:428, 거래세:257, 실거래금액:855315, 상태:"양호" },
  { id:15, 거래일자:"2026-06-16", 종목명:"현대차",           거래구분:"매도", 수량:2,  거래단가:238000, 거래금액:476000,  수수료:238, 거래세:143, 실거래금액:475619, 상태:"위험" },
  { id:16, 거래일자:"2026-06-15", 종목명:"LG화학",           거래구분:"매수", 수량:2,  거래단가:298000, 거래금액:596000,  수수료:298, 거래세:179, 실거래금액:595523, 상태:"양호" },
  { id:17, 거래일자:"2026-06-14", 종목명:"삼성전자",         거래구분:"매수", 수량:5,  거래단가:65400,  거래금액:327000,  수수료:164, 거래세:98,  실거래금액:326738, 상태:"경고" },
  { id:18, 거래일자:"2026-06-13", 종목명:"기아",             거래구분:"매수", 수량:6,  거래단가:96800,  거래금액:580800,  수수료:290, 거래세:174, 실거래금액:580336, 상태:"양호" },
  { id:19, 거래일자:"2026-06-12", 종목명:"셀트리온",         거래구분:"매도", 수량:4,  거래단가:182000, 거래금액:728000,  수수료:364, 거래세:218, 실거래금액:727418, 상태:"위험" },
  { id:20, 거래일자:"2026-06-11", 종목명:"POSCO홀딩스",      거래구분:"매도", 수량:2,  거래단가:318000, 거래금액:636000,  수수료:318, 거래세:191, 실거래금액:635491, 상태:"경고" },
];

const STATUS_COLOR = { 위험: '#FF8A00', 경고: '#FDE047', 양호: '#6EE7B7' };
const TYPE_STYLE   = {
  매수: { color: '#F43F5E ', bg: 'rgba(244,63,94,0.15)' },
  매도: { color: '#60A5FA', bg: 'rgba(96,165,250,0.15)' },
};
const PAGE_SIZE = 15;

const TRIGGERED_RULES = ['손절회피', '고점추격', '과도한 매매빈도'];

function GaugeChart({ score }) {
  const r = 36, cx = 50, cy = 50;
  const circ = 2 * Math.PI * r;
  const fillArc = circ * Math.min(score, 1);
  const color = score >= 0.6 ? '#FF8A00' : '#6EE7B7';
  const label = score >= 0.6 ? '위험' : '양호';
  return (
    <svg width="90" height="90" viewBox="0 0 100 100">
      <circle cx={cx} cy={cy} r={r} fill="none" stroke="#2D3748" strokeWidth="8" />
      <circle cx={cx} cy={cy} r={r} fill="none" stroke={color} strokeWidth="8"
        strokeDasharray={`${fillArc} ${circ}`} strokeLinecap="round"
        transform={`rotate(-90 ${cx} ${cy})`} />
      <text x={cx} y={cy - 2} textAnchor="middle" fill={color} fontSize="14" fontWeight="600">{score.toFixed(2)}</text>
      <text x={cx} y={cy + 14} textAnchor="middle" fill={color} fontSize="11">{label}</text>
    </svg>
  );
}

export default function Report() {
  const [sortAsc, setSortAsc]             = useState(false);
  const [typeFilter, setTypeFilter]       = useState('전체');
  const [statusFilters, setStatusFilters] = useState([]);
  const [search, setSearch]               = useState('');
  const [page, setPage]                   = useState(1);
  const [selected, setSelected]           = useState(null);

  const filtered = useMemo(() => {
    let data = [...SAMPLE_DATA];
    if (typeFilter !== '전체') data = data.filter(r => r.거래구분 === typeFilter);
    if (statusFilters.length > 0) data = data.filter(r => statusFilters.includes(r.상태));
    if (search.trim()) {
      const q = search.trim().toLowerCase();
      data = data.filter(r => r.종목명.toLowerCase().includes(q) || r.거래일자.includes(q));
    }
    data.sort((a, b) => {
      const d = new Date(a.거래일자) - new Date(b.거래일자);
      return sortAsc ? d : -d;
    });
    return data;
  }, [sortAsc, typeFilter, statusFilters, search]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const pageData   = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  const toggleStatus = (st) => {
    setStatusFilters(prev => prev.includes(st) ? prev.filter(x => x !== st) : [...prev, st]);
    setPage(1);
  };

  return (
    <div style={s.page}>
      <div>
        <h2 style={s.title}>전체 매매 내역</h2>
        <p style={s.subtitle}>분석하고 싶은 거래를 선택하세요</p>
      </div>

      {/* ── 필터바 ── */}
      <div style={s.filterBar}>
        <div style={s.filterLeft}>
          <button
            onClick={() => { setSortAsc(p => !p); setPage(1); }}
            style={{
              ...s.sortBtn,
              borderColor: sortAsc ? '#60A5FA' : '#334155',
              background: sortAsc ? 'rgba(96,165,250,0.1)' : 'none',
            }}
            title={sortAsc ? '오래된순' : '최신순'}
          >
            <ArrowUpDown size={15} color={sortAsc ? '#60A5FA' : '#94A3B8'} />
          </button>

          <div style={{ position: 'relative' }}>
            <select
              value={typeFilter}
              onChange={e => { setTypeFilter(e.target.value); setPage(1); }}
              style={s.select}
            >
              {['전체', '매수', '매도'].map(v => <option key={v}>{v}</option>)}
            </select>
            <span style={s.selectArrow}>▾</span>
          </div>

          {['위험', '경고', '양호'].map(st => {
            const on = statusFilters.includes(st);
            return (
              <label key={st} style={{ cursor: 'pointer', userSelect: 'none', display: 'inline-flex', alignItems: 'center', gap: 7 }}>
                <input type="checkbox" checked={on} onChange={() => toggleStatus(st)} style={{ display: 'none' }} />
                <span style={{
                  width: 15, height: 15, borderRadius: 4, flexShrink: 0,
                  border: `1.5px solid ${on ? '#94A3B8' : '#475569'}`,
                  background: on ? 'rgba(148,163,184,0.18)' : 'transparent',
                  display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                  transition: 'all 0.15s',
                }}>
                  {on && (
                    <svg width="9" height="9" viewBox="0 0 9 9" fill="none">
                      <path d="M1.5 4.5L3.5 6.5L7.5 2.5" stroke="#94A3B8" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                  )}
                </span>
                <span style={{ fontSize: 13, color: '#94A3B8' }}>{st}</span>
              </label>
            );
          })}
        </div>

        <div style={s.searchBar}>
          <Search size={14} color="#94A3B8" />
          <input
            value={search}
            onChange={e => { setSearch(e.target.value); setPage(1); }}
            placeholder="종목명을 검색하세요"
            style={s.searchInput}
          />
          <span style={s.slash}>/</span>
        </div>
      </div>

      {/* ── 테이블 ── */}
      <div style={s.tableWrapper}>
        <table style={s.table}>
          <thead>
            <tr>
              {['거래일자','종목명','거래구분','수량','거래단가','거래금액','수수료','거래세','실거래금액','상태'].map(h => (
                <th key={h} style={s.th}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {pageData.map((row, idx) => (
              <tr
                key={row.id}
                onClick={() => setSelected(row)}
                style={{
                  ...s.tr,
                  borderBottom: idx === pageData.length - 1 ? 'none' : '1px solid rgba(51,65,85,0.5)',
                  background: selected?.id === row.id ? 'rgba(148,163,184,0.07)' : 'transparent',
                }}
              >
                <td style={s.td}>{row.거래일자}</td>
                <td style={s.td}>{row.종목명}</td>
                <td style={s.td}>
                  <span style={{
                    ...s.badge,
                    color: TYPE_STYLE[row.거래구분].color,
                    background: TYPE_STYLE[row.거래구분].bg,
                  }}>{row.거래구분}</span>
                </td>
                <td style={s.td}>{row.수량.toLocaleString()}</td>
                <td style={s.td}>{row.거래단가.toLocaleString()}</td>
                <td style={s.td}>{row.거래금액.toLocaleString()}</td>
                <td style={s.td}>{row.수수료.toLocaleString()}</td>
                <td style={s.td}>{row.거래세.toLocaleString()}</td>
                <td style={s.td}>{row.실거래금액.toLocaleString()}</td>
                <td style={s.td}>
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}>
                    <span style={{ width: 7, height: 7, borderRadius: '50%', background: STATUS_COLOR[row.상태], flexShrink: 0 }} />
                    <span style={{ color: STATUS_COLOR[row.상태] }}>{row.상태}</span>
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* ── 상세 패널 ── */}
      <div style={{
        ...s.detailPanel,
        transform: selected ? 'translateX(0)' : 'translateX(100%)',
        transition: 'transform 0.25s cubic-bezier(0.4,0,0.2,1)',
      }}>
        <div style={s.panelHeader}>
          <span style={{ fontSize: 15, fontWeight: 600, color: '#F8FAFC' }}>{selected?.종목명}</span>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <span style={{ fontSize: 12, color: '#94A3B8' }}>분석일: 2026-05-28</span>
            <button onClick={() => setSelected(null)} style={s.closeBtn}><X size={16} /></button>
          </div>
        </div>

        <div style={s.panelBody}>
          {/* 카드 1 — 거래 상세 */}
          <div style={s.card}>
            <p style={s.cardTitle}>거래 상세</p>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', rowGap: 14 }}>
              {[
                { label: '거래구분', badge: true },
                { label: '거래일자', value: '2025-12-31' },
                { label: '거래단가', value: '66,800원' },
                { label: '수량', value: '10주' },
                { label: '거래금액', value: '668,000원' },
                { label: '수수료', value: '334원' },
                { label: '거래세', value: '201원' },
                { label: '실거래금액', value: '667,465원' },
              ].map(({ label, value, badge }) => (
                <div key={label}>
                  <p style={{ fontSize: 12, color: '#94A3B8', marginBottom: 5 }}>{label}</p>
                  {badge
                    ? <span style={{ ...s.badge, color: TYPE_STYLE['매수'].color, background: TYPE_STYLE['매수'].bg }}>매수</span>
                    : <p style={{ fontSize: 15, fontWeight: 600, color: '#F8FAFC' }}>{value}</p>
                  }
                </div>
              ))}
            </div>
          </div>

          {/* 카드 2 — 위험도 분석 */}
          <div style={s.card}>
            <p style={s.cardTitle}>위험도 분석</p>
            <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
              <GaugeChart score={0.35} />
              <div style={{ flex: 1 }}>
                {[
                  { label: 'Rule', value: 0.00, isNA: false },
                  { label: 'Statistical', value: 0.50, isNA: false },
                  { label: 'LSTM', value: 0, isNA: true },
                ].map(({ label, value, isNA }) => (
                  <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
                    <span style={{ width: 72, fontSize: 12, color: '#94A3B8', flexShrink: 0 }}>{label}</span>
                    <div style={{ flex: 1, height: 4, background: '#0F172A', borderRadius: 2 }}>
                      {!isNA && value > 0 && (
                        <div style={{ width: `${value * 100}%`, height: '100%', background: '#F8FAFC', borderRadius: 2 }} />
                      )}
                    </div>
                    <span style={{ width: 28, fontSize: 12, textAlign: 'right', flexShrink: 0, color: isNA ? '#94A3B8' : '#F8FAFC' }}>
                      {isNA ? '-' : value.toFixed(2)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* 카드 3 — 행동 이탈 지수 */}
          {(() => {
            const dev = 1.75;
            const devColor = dev < 2.0 ? '#6EE7B7' : dev < 3.0 ? '#FDE047' : '#FF8A00';
            const devBadge = dev < 2.0
              ? { label: '양호', color: '#6EE7B7', bg: 'rgba(110,231,183,0.3)' }
              : dev < 3.0
              ? { label: '경고', color: '#FDE047', bg: 'rgba(253,224,71,0.3)' }
              : { label: '위험', color: '#FF8A00', bg: 'rgba(255,138,0,0.3)' };
            return (
              <div style={s.card}>
                <p style={s.cardTitle}>행동 이탈 지수</p>
                <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 14 }}>
                  <div>
                    <p style={{ fontSize: 22, fontWeight: 700, color: devColor, lineHeight: 1.2 }}>{dev}</p>
                    <p style={{ fontSize: 12, color: '#94A3B8', marginTop: 4 }}>평소 매매 패턴 대비 이탈 정도</p>
                  </div>
                  <span style={{ fontSize: 12, fontWeight: 600, color: devBadge.color, background: devBadge.bg, padding: '4px 12px', borderRadius: 999 }}>{devBadge.label}</span>
                </div>
                <div style={{ background: '#2D3748', borderRadius: 4, height: 8, overflow: 'hidden' }}>
                  <div style={{ width: `${Math.min(dev / 4.0, 1) * 100}%`, height: '100%', background: devColor, borderRadius: 4 }} />
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 6 }}>
                  {['0', '1.0', '2.0', '3.0', '4.0+'].map(t => <span key={t} style={{ fontSize: 11, color: '#94A3B8' }}>{t}</span>)}
                </div>
              </div>
            );
          })()}

          {/* 카드 4 — 탐지된 패턴 */}
          <div style={s.card}>
            <p style={s.cardTitle}>탐지된 패턴</p>
            {TRIGGERED_RULES.length === 0
              ? <p style={{ fontSize: 13, color: '#94A3B8' }}>탐지된 이상 패턴 없음</p>
              : <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {TRIGGERED_RULES.map(rule => (
                    <div key={rule} style={{
                      background: 'linear-gradient(90deg, rgba(148,163,184,0.15), transparent)',
                      borderLeft: '2px solid #94A3B8',
                      padding: '7px 10px',
                      fontSize: 13,
                      color: '#F8FAFC',
                    }}>{rule}</div>
                  ))}
                </div>
            }
          </div>
        </div>
      </div>

      {/* ── 페이지네이션 ── */}
      <div style={s.pagination}>
        <button
          onClick={() => setPage(p => Math.max(1, p - 1))}
          disabled={page === 1}
          style={{ ...s.pageBtn, opacity: page === 1 ? 0.35 : 1, cursor: page === 1 ? 'default' : 'pointer' }}
        >
          <ChevronLeft size={14} />
        </button>
        {Array.from({ length: totalPages }, (_, i) => i + 1).map(n => (
          <button
            key={n}
            onClick={() => setPage(n)}
            style={{ ...s.pageBtn, ...(n === page ? s.pageBtnActive : {}) }}
          >
            {n}
          </button>
        ))}
        <button
          onClick={() => setPage(p => Math.min(totalPages, p + 1))}
          disabled={page === totalPages}
          style={{ ...s.pageBtn, opacity: page === totalPages ? 0.35 : 1, cursor: page === totalPages ? 'default' : 'pointer' }}
        >
          <ChevronRight size={14} />
        </button>
      </div>
    </div>
  );
}

// ── 스타일 ────────────────────────────────────────────────────
const s = {
  page: {
    padding: '32px 40px',
    display: 'flex',
    flexDirection: 'column',
    gap: 20,
  },
  title: {
    fontSize: 15,
    fontWeight: 600,
    color: '#F8FAFC',
    marginBottom: 10,
  },
  subtitle: {
    fontSize: 14,
    color: '#94A3B8',
  },
  filterBar: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  filterLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
  },
  sortBtn: {
    background: 'none',
    border: '1px solid #334155',
    borderRadius: 8,
    padding: '6px 10px',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
  },
  select: {
    background: '#1E293B',
    border: '1px solid #334155',
    borderRadius: 8,
    padding: '6px 32px 6px 12px',
    color: '#F8FAFC',
    fontSize: 13,
    cursor: 'pointer',
    outline: 'none',
    fontFamily: 'Inter, sans-serif',
    appearance: 'none',
    WebkitAppearance: 'none',
  },
  selectArrow: {
    position: 'absolute',
    right: 10,
    top: '50%',
    transform: 'translateY(-50%)',
    color: '#64748B',
    fontSize: 11,
    pointerEvents: 'none',
  },
  searchBar: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    background: '#1E293B',
    border: '1px solid #334155',
    borderRadius: 8,
    padding: '6px 12px',
    width: 200,
  },
  searchInput: {
    background: 'none',
    border: 'none',
    outline: 'none',
    color: '#F8FAFC',
    fontSize: 13,
    flex: 1,
    fontFamily: 'Inter, sans-serif',
  },
  slash: {
    fontSize: 11,
    color: '#94A3B8',
    background: '#334155',
    padding: '1px 6px',
    borderRadius: 4,
    lineHeight: 1.6,
    flexShrink: 0,
  },
  tableWrapper: {
    background: '#1E293B',
    borderRadius: 16,
    padding: '16px 24px',
    minWidth: 900,
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
  },
  th: {
    fontSize: 12,
    color: '#64748B',
    fontWeight: 500,
    textAlign: 'left',
    padding: '14px 16px',
    borderBottom: '1px solid #334155',
    whiteSpace: 'nowrap',
  },
  tr: {
    borderBottom: '1px solid rgba(51,65,85,0.5)',
    cursor: 'pointer',
  },
  td: {
    fontSize: 13,
    color: '#F8FAFC',
    padding: '12px 16px',
    whiteSpace: 'nowrap',
  },
  badge: {
    display: 'inline-block',
    fontSize: 11,
    fontWeight: 600,
    padding: '3px 10px',
    borderRadius: 999,
  },
  detailPanel: {
    position: 'fixed',
    top: 60,
    right: 0,
    bottom: 0,
    width: 420,
    background: '#0F172A',
    borderLeft: '1px solid #334155',
    display: 'flex',
    flexDirection: 'column',
    zIndex: 50,
  },
  panelHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '20px 24px',
    borderBottom: '1px solid #334155',
    flexShrink: 0,
  },
  panelTitle: {
    fontSize: 15,
    fontWeight: 600,
    color: '#F8FAFC',
  },
  closeBtn: {
    background: 'none',
    border: 'none',
    color: '#64748B',
    cursor: 'pointer',
    padding: 4,
    display: 'flex',
    alignItems: 'center',
    borderRadius: 6,
  },
  panelBody: {
    padding: '20px 24px',
    display: 'flex',
    flexDirection: 'column',
    gap: 16,
    flex: 1,
    overflowY: 'auto',
  },
  card: {
    background: '#1E293B',
    borderRadius: 12,
    padding: '18px 20px',
  },
  cardTitle: {
    fontSize: 14,
    fontWeight: 500,
    color: '#F8FAFC',
    marginBottom: 14,
  },
  pagination: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    paddingBottom: 8,
  },
  pageBtn: {
    background: 'none',
    border: '1px solid #475569',
    borderRadius: 16,
    minWidth: 34,
    height: 34,
    padding: '0 10px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: '#94A3B8',
    fontSize: 13,
    cursor: 'pointer',
    fontFamily: 'Inter, sans-serif',
  },
  pageBtnActive: {
    background: '#1E293B',
    color: '#F8FAFC',
    borderColor: '#475569',
  },
};
