import { useState, useMemo } from 'react';
import { ArrowUpDown, Search, X, ChevronLeft, ChevronRight } from 'lucide-react';

const STATUS_COLOR = { 위험: '#FF8A00', 경고: '#FDE047', 양호: '#6EE7B7' };
const TYPE_STYLE   = {
  매수: { color: '#F43F5E', bg: 'rgba(244,63,94,0.15)' },
  매도: { color: '#60A5FA', bg: 'rgba(96,165,250,0.15)' },
};
const PAGE_SIZE = 15;

function GaugeChart({ score }) {
  const r = 36, cx = 50, cy = 50;
  const circ    = 2 * Math.PI * r;
  const fillArc = circ * Math.min(score / 100, 1);
  const color   = score >= 60 ? '#FF8A00' : '#6EE7B7';
  const label   = score >= 60 ? '위험' : '양호';
  return (
    <svg width="90" height="90" viewBox="0 0 100 100">
      <circle cx={cx} cy={cy} r={r} fill="none" stroke="#2D3748" strokeWidth="8" />
      <circle cx={cx} cy={cy} r={r} fill="none" stroke={color} strokeWidth="8"
        strokeDasharray={`${fillArc} ${circ}`} strokeLinecap="round"
        transform={`rotate(-90 ${cx} ${cy})`} />
      <text x={cx} y={cy - 2} textAnchor="middle" fill={color} fontSize="14" fontWeight="600">{score}</text>
      <text x={cx} y={cy + 14} textAnchor="middle" fill={color} fontSize="11">{label}</text>
    </svg>
  );
}

export default function Report({ trades = [], analysis = [] }) {
  const [sortAsc, setSortAsc]             = useState(false);
  const [typeFilter, setTypeFilter]       = useState('전체');
  const [statusFilters, setStatusFilters] = useState([]);
  const [search, setSearch]               = useState('');
  const [page, setPage]                   = useState(1);
  const [selected, setSelected]           = useState(null);

  // ── analysis 검색용 맵: "종목명_날짜" → analysisRecord ──────
  const analysisMap = useMemo(() => {
    const map = {};
    analysis.forEach(a => {
      const key = `${a.xai_result?.종목명}_${a.xai_result?.날짜}`;
      if (!map[key]) map[key] = a;
    });
    return map;
  }, [analysis]);

  const getAnalysis  = (t) => analysisMap[`${t.종목명}_${String(t.거래일자)}`] || null;
  const getStatus    = (t) => { const a = getAnalysis(t); return a ? (a.is_anomaly ? '위험' : '양호') : '양호'; };

  const filtered = useMemo(() => {
    let data = [...trades];
    if (typeFilter !== '전체') data = data.filter(r => r.거래구분 === typeFilter);
    if (statusFilters.length > 0) data = data.filter(r => statusFilters.includes(getStatus(r)));
    if (search.trim()) {
      const q = search.trim().toLowerCase();
      data = data.filter(r => r.종목명.toLowerCase().includes(q) || String(r.거래일자).includes(q));
    }
    data.sort((a, b) => {
      const d = new Date(a.거래일자) - new Date(b.거래일자);
      return sortAsc ? d : -d;
    });
    return data;
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [trades, analysisMap, sortAsc, typeFilter, statusFilters, search]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const pageData   = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  const toggleStatus = (st) => {
    setStatusFilters(prev => prev.includes(st) ? prev.filter(x => x !== st) : [...prev, st]);
    setPage(1);
  };

  // ── 선택된 거래의 분석 데이터 ─────────────────────────────────
  const selAnalysis  = selected ? getAnalysis(selected) : null;
  const finalScore   = selAnalysis ? Math.round((selAnalysis.final_score  || 0) * 100) : 0;
  const ruleScore    = selAnalysis ? Math.round((selAnalysis.rule_score   || 0) * 100) : 0;
  const statScore    = selAnalysis ? Math.round((selAnalysis.stat_score   || 0) * 100) : 0;
  const lstmScore    = selAnalysis?.lstm_score != null ? Math.round(selAnalysis.lstm_score * 100) : null;
  const mahalanobis  = selAnalysis?.xai_result?.mahalanobis ?? 0;
  const triggeredRules = selAnalysis?.xai_result?.triggered_rules ?? [];
  const analyzedAt   = selected?.created_at?.slice(0, 10) ?? '-';

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
            style={{ ...s.sortBtn, borderColor: sortAsc ? '#60A5FA' : '#334155', background: sortAsc ? 'rgba(96,165,250,0.1)' : 'none' }}
            title={sortAsc ? '오래된순' : '최신순'}
          >
            <ArrowUpDown size={15} color={sortAsc ? '#60A5FA' : '#94A3B8'} />
          </button>

          <div style={{ position: 'relative' }}>
            <select value={typeFilter} onChange={e => { setTypeFilter(e.target.value); setPage(1); }} style={s.select}>
              {['전체', '매수', '매도'].map(v => <option key={v}>{v}</option>)}
            </select>
            <span style={s.selectArrow}>▾</span>
          </div>

          {['위험', '양호'].map(st => {
            const on = statusFilters.includes(st);
            return (
              <label key={st} style={{ cursor: 'pointer', userSelect: 'none', display: 'inline-flex', alignItems: 'center', gap: 7 }}>
                <input type="checkbox" checked={on} onChange={() => toggleStatus(st)} style={{ display: 'none' }} />
                <span style={{ width: 15, height: 15, borderRadius: 4, flexShrink: 0, border: `1.5px solid ${on ? '#94A3B8' : '#475569'}`, background: on ? 'rgba(148,163,184,0.18)' : 'transparent', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', transition: 'all 0.15s' }}>
                  {on && <svg width="9" height="9" viewBox="0 0 9 9" fill="none"><path d="M1.5 4.5L3.5 6.5L7.5 2.5" stroke="#94A3B8" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>}
                </span>
                <span style={{ fontSize: 13, color: '#94A3B8' }}>{st}</span>
              </label>
            );
          })}
        </div>

        <div style={s.searchBar}>
          <Search size={14} color="#94A3B8" />
          <input value={search} onChange={e => { setSearch(e.target.value); setPage(1); }} placeholder="종목명을 검색하세요" style={s.searchInput} />
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
            {pageData.length === 0 ? (
              <tr><td colSpan={10} style={{ ...s.td, textAlign: 'center', color: '#94A3B8', padding: '32px 0' }}>데이터가 없습니다</td></tr>
            ) : pageData.map((row, idx) => {
              const st = getStatus(row);
              return (
                <tr
                  key={row.id}
                  onClick={() => setSelected(row)}
                  style={{ ...s.tr, borderBottom: idx === pageData.length - 1 ? 'none' : '1px solid rgba(51,65,85,0.5)', background: selected?.id === row.id ? 'rgba(148,163,184,0.07)' : 'transparent' }}
                >
                  <td style={s.td}>{String(row.거래일자)}</td>
                  <td style={s.td}>{row.종목명}</td>
                  <td style={s.td}>
                    <span style={{ ...s.badge, color: TYPE_STYLE[row.거래구분]?.color, background: TYPE_STYLE[row.거래구분]?.bg }}>{row.거래구분}</span>
                  </td>
                  <td style={s.td}>{Number(row.거래수량).toLocaleString()}</td>
                  <td style={s.td}>₩{Number(row.거래단가).toLocaleString()}</td>
                  <td style={s.td}>₩{Number(row.거래금액).toLocaleString()}</td>
                  <td style={s.td}>₩{Number(row.수수료).toLocaleString()}</td>
                  <td style={s.td}>₩{Number(row.거래세).toLocaleString()}</td>
                  <td style={s.td}>₩{(row.거래구분 === '매수' ? Math.abs(Number(row.정산금액)) : Number(row.정산금액)).toLocaleString()}</td>
                  <td style={s.td}>
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}>
                      <span style={{ width: 7, height: 7, borderRadius: '50%', background: STATUS_COLOR[st], flexShrink: 0 }} />
                      <span style={{ color: STATUS_COLOR[st] }}>{st}</span>
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* ── 상세 패널 ── */}
      <div style={{ ...s.detailPanel, transform: selected ? 'translateX(0)' : 'translateX(100%)', transition: 'transform 0.25s cubic-bezier(0.4,0,0.2,1)' }}>
        <div style={s.panelHeader}>
          <span style={{ fontSize: 15, fontWeight: 600, color: '#F8FAFC' }}>{selected?.종목명}</span>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <span style={{ fontSize: 12, color: '#94A3B8' }}>분석일: {analyzedAt}</span>
            <button onClick={() => setSelected(null)} style={s.closeBtn}><X size={16} /></button>
          </div>
        </div>

        <div style={s.panelBody}>
          {/* 카드 1 — 거래 상세 */}
          <div style={s.card}>
            <p style={s.cardTitle}>거래 상세</p>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', rowGap: 14 }}>
              {selected && [
                { label: '거래구분',  badge: true },
                { label: '거래일자',  value: String(selected.거래일자) },
                { label: '거래단가',  value: `${Number(selected.거래단가).toLocaleString()}원` },
                { label: '수량',     value: `${Number(selected.거래수량).toLocaleString()}주` },
                { label: '거래금액',  value: `${Number(selected.거래금액).toLocaleString()}원` },
                { label: '수수료',   value: `${Number(selected.수수료).toLocaleString()}원` },
                { label: '거래세',   value: `${Number(selected.거래세).toLocaleString()}원` },
                { label: '정산금액',  value: `${Number(selected.정산금액).toLocaleString()}원` },
              ].map(({ label, value, badge }) => (
                <div key={label}>
                  <p style={{ fontSize: 11, color: '#94A3B8', marginBottom: 5 }}>{label}</p>
                  {badge
                    ? <span style={{ ...s.badge, color: TYPE_STYLE[selected.거래구분]?.color, background: TYPE_STYLE[selected.거래구분]?.bg }}>{selected.거래구분}</span>
                    : <p style={{ fontSize: 14, fontWeight: 500, color: '#F8FAFC' }}>{value}</p>
                  }
                </div>
              ))}
            </div>
          </div>

          {/* 카드 2 — 위험도 분석 */}
          <div style={s.card}>
            <p style={s.cardTitle}>위험도 분석</p>
            <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
              <GaugeChart score={finalScore} />
              <div style={{ flex: 1 }}>
                {[
                  { label: 'Rule',        value: ruleScore, isNA: false },
                  { label: 'Statistical', value: statScore, isNA: false },
                  { label: 'LSTM',        value: lstmScore ?? 0, isNA: lstmScore == null },
                ].map(({ label, value, isNA }) => (
                  <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
                    <span style={{ width: 72, fontSize: 12, color: '#94A3B8', flexShrink: 0 }}>{label}</span>
                    <div style={{ flex: 1, height: 4, background: '#0F172A', borderRadius: 2 }}>
                      {!isNA && value > 0 && (
                        <div style={{ width: `${value}%`, height: '100%', background: '#F8FAFC', borderRadius: 2 }} />
                      )}
                    </div>
                    <span style={{ width: 28, fontSize: 12, textAlign: 'right', flexShrink: 0, color: isNA ? '#94A3B8' : '#F8FAFC' }}>
                      {isNA ? '-' : value}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* 카드 3 — 행동 이탈 지수 */}
          {(() => {
            const dev = Number(mahalanobis) || 0;
            const devColor = dev < 2.0 ? '#6EE7B7' : dev < 3.0 ? '#FDE047' : '#FF8A00';
            const devBadge = dev < 2.0
              ? { label: '양호', color: '#6EE7B7', bg: 'rgba(110,231,183,0.3)' }
              : dev < 3.0
              ? { label: '주의', color: '#FDE047', bg: 'rgba(253,224,71,0.3)' }
              : { label: '위험', color: '#FF8A00', bg: 'rgba(255,138,0,0.3)' };
            return (
              <div style={s.card}>
                <p style={s.cardTitle}>행동 이탈 지수</p>
                <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 14 }}>
                  <div>
                    <p style={{ fontSize: 22, fontWeight: 700, color: devColor, lineHeight: 1.2 }}>{dev.toFixed(2)}</p>
                    <p style={{ fontSize: 12, color: '#94A3B8', marginTop: 4 }}>평소 매매 패턴 대비 이탈 정도</p>
                  </div>
                  <span style={{ fontSize: 12, fontWeight: 600, color: devBadge.color, background: devBadge.bg, padding: '4px 12px', borderRadius: 999 }}>{devBadge.label}</span>
                </div>
                <div style={{ background: '#2a2d3a', borderRadius: 4, height: 8, overflow: 'hidden' }}>
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
            {triggeredRules.length === 0
              ? <p style={{ fontSize: 13, color: '#94A3B8' }}>탐지된 이상 패턴 없음</p>
              : <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {triggeredRules.map((rule, i) => (
                    <div key={i} style={{ background: 'linear-gradient(90deg, rgba(148,163,184,0.15), transparent)', borderLeft: '2px solid #94A3B8', padding: '7px 10px', fontSize: 13, color: '#F8FAFC' }}>{rule}</div>
                  ))}
                </div>
            }
          </div>
        </div>
      </div>

      {/* ── 페이지네이션 ── */}
      <div style={s.pagination}>
        <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} style={{ ...s.pageBtn, opacity: page === 1 ? 0.35 : 1, cursor: page === 1 ? 'default' : 'pointer' }}>
          <ChevronLeft size={14} />
        </button>
        {(() => {
          let start = Math.max(1, Math.min(page - 2, totalPages - 4));
          let end   = Math.min(totalPages, start + 4);
          const pages = [];
          for (let i = start; i <= end; i++) pages.push(i);
          return pages.map(n => (
            <button key={n} onClick={() => setPage(n)} style={{ ...s.pageBtn, ...(n === page ? s.pageBtnActive : {}) }}>{n}</button>
          ));
        })()}
        <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages} style={{ ...s.pageBtn, opacity: page === totalPages ? 0.35 : 1, cursor: page === totalPages ? 'default' : 'pointer' }}>
          <ChevronRight size={14} />
        </button>
      </div>
    </div>
  );
}

// ── 스타일 ────────────────────────────────────────────────────────
const s = {
  page: { padding: '32px 40px', display: 'flex', flexDirection: 'column', gap: 20 },
  title:      { fontSize: 15, fontWeight: 600, color: '#F8FAFC', marginBottom: 10 },
  subtitle:   { fontSize: 14, color: '#94A3B8' },
  filterBar:  { display: 'flex', alignItems: 'center', justifyContent: 'space-between' },
  filterLeft: { display: 'flex', alignItems: 'center', gap: 10 },
  sortBtn:    { background: 'none', border: '1px solid #334155', borderRadius: 8, padding: '6px 10px', cursor: 'pointer', display: 'flex', alignItems: 'center' },
  select:     { background: '#1E293B', border: '1px solid #334155', borderRadius: 8, padding: '6px 32px 6px 12px', color: '#F8FAFC', fontSize: 13, cursor: 'pointer', outline: 'none', fontFamily: 'Inter, sans-serif', appearance: 'none', WebkitAppearance: 'none' },
  selectArrow:{ position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)', color: '#64748B', fontSize: 11, pointerEvents: 'none' },
  searchBar:  { display: 'flex', alignItems: 'center', gap: 8, background: '#1E293B', border: '1px solid #334155', borderRadius: 8, padding: '6px 12px', width: 200 },
  searchInput:{ background: 'none', border: 'none', outline: 'none', color: '#F8FAFC', fontSize: 13, flex: 1, fontFamily: 'Inter, sans-serif' },
  slash:      { fontSize: 11, color: '#94A3B8', background: '#334155', padding: '1px 6px', borderRadius: 4, lineHeight: 1.6, flexShrink: 0 },
  tableWrapper:{ background: '#1E293B', borderRadius: 16, padding: '16px 24px', minWidth: 900 },
  table:      { width: '100%', borderCollapse: 'collapse' },
  th:         { fontSize: 12, color: '#64748B', fontWeight: 500, textAlign: 'left', padding: '14px 16px', borderBottom: '1px solid #334155', whiteSpace: 'nowrap' },
  tr:         { borderBottom: '1px solid rgba(51,65,85,0.5)', cursor: 'pointer' },
  td:         { fontSize: 13, color: '#F8FAFC', padding: '12px 16px', whiteSpace: 'nowrap' },
  badge:      { display: 'inline-block', fontSize: 11, fontWeight: 600, padding: '3px 10px', borderRadius: 999 },
  detailPanel:{ position: 'fixed', top: 60, right: 0, bottom: 0, width: 420, background: '#0F172A', borderLeft: '1px solid #334155', display: 'flex', flexDirection: 'column', zIndex: 50 },
  panelHeader:{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '20px 24px', borderBottom: '1px solid #334155', flexShrink: 0 },
  closeBtn:   { background: 'none', border: 'none', color: '#64748B', cursor: 'pointer', padding: 4, display: 'flex', alignItems: 'center', borderRadius: 6 },
  panelBody:  { padding: '20px 24px', display: 'flex', flexDirection: 'column', gap: 16, flex: 1, overflowY: 'auto' },
  card:       { background: '#1E293B', borderRadius: 12, padding: '18px 20px' },
  cardTitle:  { fontSize: 13, fontWeight: 500, color: '#94A3B8', marginBottom: 14 },
  pagination: { display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6, paddingBottom: 8 },
  pageBtn:    { background: 'none', border: '1px solid #475569', borderRadius: 16, minWidth: 34, height: 34, padding: '0 10px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#94A3B8', fontSize: 13, cursor: 'pointer', fontFamily: 'Inter, sans-serif' },
  pageBtnActive: { background: '#1E293B', color: '#F8FAFC', borderColor: '#475569' },
};
