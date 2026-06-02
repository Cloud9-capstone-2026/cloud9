import { useState, useEffect, useRef, useMemo } from 'react';
import { CheckCircle, XCircle, AlertTriangle, X, ChevronLeft, ChevronRight } from 'lucide-react';
import client from '../api/client';

const COL_ROWS = [
  ['거래일자', '종목명', '거래구분'],
  ['거래수량', '거래단가', '거래금액'],
  ['수수료', '거래세', '정산금액'],
];

export default function Upload({ onNavigate, onComplete, trades = [], uploads = [] }) {
  const [phase, setPhase]               = useState('idle');
  const [file, setFile]                 = useState(null);
  const [progress, setProgress]         = useState(0);
  const [uploadResult, setUploadResult] = useState(null);  // { count, upload_id }
  const [analysisResult, setAnalysisResult] = useState(null); // array
  const [uploadError, setUploadError]   = useState('');
  const [histPage, setHistPage]         = useState(1);
  const fileInputRef = useRef(null);
  const timerRef     = useRef(null);

  const HIST_PAGE_SIZE = 5;

  // ── 업로드 히스토리: trades를 upload_id 기준으로 그룹핑 ──────
  const historyGroups = useMemo(() => {
    const uploadMap = {};
    uploads.forEach(u => { uploadMap[u.id] = u; });
    const map = {};
    trades.forEach(t => {
      const uid = t.upload_id;
      if (uid == null) return;
      if (!map[uid]) map[uid] = {
        upload_id: uid,
        count: 0,
        created_at: t.created_at,
        file_name: uploadMap[uid]?.file_name ?? `업로드 #${uid}`,
      };
      map[uid].count++;
      if (t.created_at && t.created_at < map[uid].created_at) map[uid].created_at = t.created_at;
    });
    return Object.values(map).sort((a, b) => b.upload_id - a.upload_id);
  }, [trades, uploads]);

  const histTotalPages = Math.max(1, Math.ceil(historyGroups.length / HIST_PAGE_SIZE));
  const historyPage    = historyGroups.slice((histPage - 1) * HIST_PAGE_SIZE, histPage * HIST_PAGE_SIZE);

  // ── 진행률 애니메이션 (API 완료 전까지 95%까지 진행) ──────────
  useEffect(() => {
    if (phase !== 'uploading' && phase !== 'analyzing') {
      setProgress(0);
      return;
    }
    setProgress(0);
    let cur = 0;
    timerRef.current = setInterval(() => {
      cur = Math.min(cur + 2, 95);
      setProgress(cur);
      if (cur >= 95) clearInterval(timerRef.current);
    }, 80);
    return () => clearInterval(timerRef.current);
  }, [phase]);

  const handleFileSelect = (f) => { setFile(f); setPhase('selected'); };
  const handleInputChange = (e) => {
    const f = e.target.files[0];
    if (f) handleFileSelect(f);
    e.target.value = '';
  };

  // ── 실제 업로드 API 호출 ──────────────────────────────────────
  const handleUploadStart = async (e) => {
    e.stopPropagation();
    setPhase('uploading');
    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await client.post('/trades/upload', formData);
      clearInterval(timerRef.current);
      const match = res.data.message?.match(/(\d+)/);
      setUploadResult({ count: match ? parseInt(match[1]) : 0, upload_id: res.data.upload_id });
      setProgress(100);
      setPhase('upload_success');
    } catch (err) {
      clearInterval(timerRef.current);
      setUploadError(err.response?.data?.detail || '업로드 중 오류가 발생했습니다.');
      setPhase('upload_fail');
    }
  };

  // ── 분석 결과 조회 ────────────────────────────────────────────
  const handleAnalyze = async () => {
    setPhase('analyzing');
    try {
      const res = await client.get('/analysis/');
      clearInterval(timerRef.current);
      setAnalysisResult(res.data || []);
      setProgress(100);
      await onComplete?.();
      setPhase('complete');
    } catch (err) {
      clearInterval(timerRef.current);
      setUploadError(err.response?.data?.detail || '분석 결과 조회에 실패했습니다.');
      setPhase('upload_fail');
    }
  };

  const fmtSize = (b) => {
    if (!b) return '';
    return b < 1048576 ? `${(b / 1024).toFixed(1)} KB` : `${(b / 1048576).toFixed(1)} MB`;
  };

  const today = new Date().toISOString().slice(0, 10).replace(/-/g, '/');
  const isCenter = !['idle', 'selected'].includes(phase);

  // ── Shared helpers ────────────────────────────────────────────
  const renderInfoBox = (rows) => (
    <div style={s.infoBox}>
      {rows.map(({ label, value }, i) => (
        <div key={label} style={{ ...s.infoRow, borderBottom: i < rows.length - 1 ? '1px solid rgba(51,65,85,0.5)' : 'none' }}>
          <span style={s.infoLbl}>{label}</span>
          <span style={s.infoVal}>{value}</span>
        </div>
      ))}
    </div>
  );

  // ── State renderers ───────────────────────────────────────────
  const renderUploadArea = () => (
    <div style={s.colLayout}>
      {/* Upload Card */}
      <div style={s.card}>
        <p style={s.cardTitle}>파일 업로드</p>
        <div
          style={phase === 'idle' ? s.dzIdle : s.dzSelected}
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => { e.preventDefault(); const f = e.dataTransfer.files[0]; if (f) handleFileSelect(f); }}
          onClick={phase === 'idle' ? () => fileInputRef.current?.click() : undefined}
        >
          {phase === 'idle' ? (
            <>
              <span style={{ fontSize: 44, lineHeight: 1 }}>📂</span>
              <p style={s.dzText}>CSV / 엑셀 파일을 드래그하거나 클릭해 업로드</p>
              <p style={s.dzSub}>지원 형식: .csv, .xlsx, .xls / 최대 10MB</p>
              <button style={s.fileSelBtn} onClick={(e) => { e.stopPropagation(); fileInputRef.current?.click(); }}>파일 선택</button>
            </>
          ) : (
            <>
              <div style={s.filePreview}>
                <span style={{ fontSize: 32, lineHeight: 1, flexShrink: 0 }}>📊</span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <p style={s.fileName}>{file?.name}</p>
                  <p style={s.fileSize}>{fmtSize(file?.size)}</p>
                </div>
                <button style={s.removeBtn} onClick={(e) => { e.stopPropagation(); setFile(null); setPhase('idle'); }}>
                  <X size={16} />
                </button>
              </div>
              <div style={s.btnRow}>
                <button style={{ ...s.fillBtn, flex: 1 }} onClick={handleUploadStart}>업로드 시작</button>
                <button style={{ ...s.outlineBtn, flex: 1 }} onClick={(e) => { e.stopPropagation(); fileInputRef.current?.click(); }}>다시 선택</button>
              </div>
            </>
          )}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', padding: '12px 16px', background: '#0F172A', borderRadius: 16 }}>
          <span style={{ color: '#94A3B8', fontSize: 12, fontWeight: 600, flexShrink: 0, marginRight: 12 }}>필수 컬럼:</span>
          {COL_ROWS.flat().flatMap((col, i, arr) =>
            i < arr.length - 1
              ? [<span key={col} style={{ flex: 1, textAlign: 'center', color: '#94A3B8', fontSize: 12 }}>{col}</span>, <span key={`sep-${i}`} style={{ color: '#334155', fontSize: 13, flexShrink: 0 }}>|</span>]
              : [<span key={col} style={{ flex: 1, textAlign: 'center', color: '#94A3B8', fontSize: 12 }}>{col}</span>]
          )}
        </div>
      </div>

      {/* History Card */}
      <div style={s.card}>
        <p style={s.histTitle}>업로드 히스토리</p>
        <table style={s.histTable}>
          <colgroup>
            <col style={{ width: '28%' }} /><col style={{ width: '40%' }} />
            <col style={{ width: '16%' }} /><col style={{ width: '16%' }} />
          </colgroup>
          <thead>
            <tr>{['날짜', '파일명', '건수', '상태'].map(h => <th key={h} style={s.histTh}>{h}</th>)}</tr>
          </thead>
          <tbody>
            {historyPage.length === 0 ? (
              <tr><td colSpan={4} style={{ ...s.histTd, color: '#94A3B8', textAlign: 'center', padding: '20px 0' }}>업로드 내역이 없습니다</td></tr>
            ) : historyPage.map((row, i) => (
              <tr key={row.upload_id} style={i < historyPage.length - 1 ? s.histTr : {}}>
                <td style={s.histTd}>{row.created_at?.slice(0, 10) ?? '-'}</td>
                <td style={s.histTd}>{row.file_name}</td>
                <td style={s.histTd}>{row.count}건</td>
                <td style={s.histTd}><span style={s.okBadge}>완료</span></td>
              </tr>
            ))}
          </tbody>
        </table>
        {histTotalPages > 1 && (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6, marginTop: 12 }}>
            <button onClick={() => setHistPage(p => Math.max(1, p - 1))} disabled={histPage === 1} style={{ ...s.pageBtn, opacity: histPage === 1 ? 0.35 : 1 }}><ChevronLeft size={13} /></button>
            {Array.from({ length: histTotalPages }, (_, i) => i + 1).map(n => (
              <button key={n} onClick={() => setHistPage(n)} style={{ ...s.pageBtn, ...(n === histPage ? s.pageBtnActive : {}) }}>{n}</button>
            ))}
            <button onClick={() => setHistPage(p => Math.min(histTotalPages, p + 1))} disabled={histPage === histTotalPages} style={{ ...s.pageBtn, opacity: histPage === histTotalPages ? 0.35 : 1 }}><ChevronRight size={13} /></button>
          </div>
        )}
      </div>
    </div>
  );

  const renderProgress = (label) => (
    <div style={s.centerCol}>
      <div style={s.spinner} />
      <p style={s.pLabel}>{label}</p>
      <p style={s.pSub}>{file?.name}</p>
      <div style={s.pTrack}>
        <div style={{ ...s.pBar, width: `${progress}%` }} />
      </div>
      <p style={s.pPct}>{progress}%</p>
    </div>
  );

  const renderSuccess = () => (
    <div style={s.centerCol}>
      <div style={s.iconCircleOk}><CheckCircle size={32} color="#6EE7B7" /></div>
      <p style={s.resTitle}>업로드 성공!</p>
      <p style={s.resSub}>파일이 성공적으로 업로드되었습니다.</p>
      {renderInfoBox([
        { label: '업로드 날짜', value: today },
        { label: '파일명',     value: file?.name ?? '-' },
        { label: '총 매매 건수', value: `${uploadResult?.count ?? 0}건` },
      ])}
      <button style={s.roundBtn} onClick={handleAnalyze}>분석 시작하기 →</button>
    </div>
  );

  const renderFail = () => (
    <div style={s.centerCol}>
      <div style={s.iconCircleFail}><XCircle size={32} color="#F43F5E" /></div>
      <p style={s.resTitle}>오류 발생</p>
      <p style={s.resSub}>파일을 처리하는 중 문제가 발생했습니다.</p>
      <div style={s.errBox}>
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 6 }}>
          <AlertTriangle size={11} color="#F43F5E" style={{ marginTop: 2, flexShrink: 0 }} />
          <p style={s.errTxt}>{uploadError || '필수 컬럼 형식을 확인 후 다시 업로드해주세요.'}</p>
        </div>
      </div>
      <button style={s.roundBtn} onClick={() => { setFile(null); setPhase('idle'); setUploadError(''); }}>다시 업로드</button>
    </div>
  );

  const renderComplete = () => {
    const anomalyCount = (analysisResult || []).filter(a => a.is_anomaly).length;
    const totalCount   = uploadResult?.count || 0;
    const rate         = totalCount > 0 ? ((anomalyCount / totalCount) * 100).toFixed(1) : '0.0';
    return (
      <div style={s.centerCol}>
        <div style={s.iconCircleOk}><CheckCircle size={32} color="#6EE7B7" /></div>
        <p style={s.resTitle}>분석 완료!</p>
        <p style={s.resSub}>{totalCount}건의 매매 데이터 분석이 완료되었습니다.</p>
        {renderInfoBox([
          { label: '분석 일자',    value: today },
          { label: '이상 탐지 건수', value: `${anomalyCount}건` },
          { label: '이상 탐지율',   value: `${rate}%` },
        ])}
        <button style={s.roundBtn} onClick={() => onNavigate?.('dashboard')}>대시보드에서 확인하기 →</button>
      </div>
    );
  };

  const renderContent = () => {
    switch (phase) {
      case 'idle':
      case 'selected':       return renderUploadArea();
      case 'uploading':      return renderProgress('파일 업로드 중...');
      case 'upload_success': return renderSuccess();
      case 'upload_fail':    return renderFail();
      case 'analyzing':      return renderProgress('매매 데이터 분석 중...');
      case 'complete':       return renderComplete();
      default:               return null;
    }
  };

  return (
    <div style={{ ...s.page, ...(isCenter ? s.pageCenter : {}) }}>
      <style>{`@keyframes spin{0%{transform:rotate(0deg)}100%{transform:rotate(360deg)}}`}</style>
      <input type="file" accept=".csv,.xlsx,.xls" ref={fileInputRef} style={{ display: 'none' }} onChange={handleInputChange} />
      {renderContent()}
    </div>
  );
}

// ── Styles ────────────────────────────────────────────────────────
const s = {
  page:       { padding: '40px', minHeight: '100%', boxSizing: 'border-box' },
  pageCenter: { display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' },
  colLayout:  { display: 'flex', flexDirection: 'column', height: '100%', gap: 32, minWidth: 700 },
  card:       { background: '#1E293B', borderRadius: 16, padding: '20px 22px', flex: 1, display: 'flex', flexDirection: 'column', gap: 16 },
  cardTitle:  { fontSize: 14, fontWeight: 600, color: '#F8FAFC', margin: 0 },
  dzIdle:     { border: '1.5px dashed rgba(148,163,184,0.4)', borderRadius: 16, minHeight: 240, display: 'flex', flex: 1, flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 10, cursor: 'pointer', padding: '24px 16px' },
  dzSelected: { border: '1.5px solid rgba(148,163,184,0.4)', borderRadius: 16, minHeight: 240, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'space-between', gap: 12, padding: '24px 16px' },
  dzText:     { fontSize: 13, color: '#F8FAFC', margin: 0, textAlign: 'center' },
  dzSub:      { fontSize: 11, color: '#94A3B8', margin: 0, textAlign: 'center' },
  fileSelBtn: { background: 'rgba(148,163,184,0.4)', color: '#F8FAFC', border: 'none', borderRadius: 8, padding: '8px 16px', fontSize: 12, fontFamily: 'Inter, sans-serif', cursor: 'pointer', marginTop: 4 },
  filePreview:{ background: '#0F172A', border: '1px solid #334155', borderRadius: 16, padding: '10px 12px', display: 'flex', alignItems: 'center', gap: 10, width: '100%', boxSizing: 'border-box' },
  fileName:   { fontSize: 12, fontWeight: 500, color: '#F8FAFC', margin: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' },
  fileSize:   { fontSize: 10, color: '#94A3B8', margin: '2px 0 0 0' },
  removeBtn:  { background: 'none', border: 'none', color: '#94A3B8', cursor: 'pointer', padding: 0, display: 'flex', alignItems: 'center', flexShrink: 0 },
  btnRow:     { display: 'flex', gap: 8, width: '100%' },
  fillBtn:    { background: 'rgba(148,163,184,0.4)', color: '#F8FAFC', border: 'none', borderRadius: 8, padding: '10px 0', fontSize: 12, fontFamily: 'Inter, sans-serif', fontWeight: 500, cursor: 'pointer' },
  outlineBtn: { background: 'transparent', color: '#F8FAFC', border: '1px solid rgba(148,163,184,0.4)', borderRadius: 8, padding: '10px 0', fontSize: 12, fontFamily: 'Inter, sans-serif', fontWeight: 500, cursor: 'pointer' },
  histTitle:  { fontSize: 14, fontWeight: 600, color: '#F8FAFC', margin: 0 },
  histTable:  { width: '100%', borderCollapse: 'collapse', marginTop: 16 },
  histTh:     { fontSize: 12, color: '#64748B', fontWeight: 500, textAlign: 'left', paddingBottom: 10, borderBottom: '1px solid #334155' },
  histTr:     { borderBottom: '1px solid rgba(51,65,85,0.5)' },
  histTd:     { fontSize: 13, color: '#F8FAFC', padding: '12px 0' },
  okBadge:    { background: 'rgba(110,231,183,0.15)', color: '#6EE7B7', borderRadius: 18, fontSize: 10, padding: '3px 8px', display: 'inline-flex', alignItems: 'center', width: 'fit-content' },
  pageBtn:    { background: 'none', border: '1px solid #475569', borderRadius: 12, minWidth: 28, height: 28, padding: '0 8px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#94A3B8', fontSize: 12, cursor: 'pointer', fontFamily: 'Inter, sans-serif' },
  pageBtnActive: { background: '#1E293B', color: '#F8FAFC', borderColor: '#475569' },
  centerCol:  { display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 14 },
  spinner:    { width: 48, height: 48, border: '4px solid #1E293B', borderTopColor: '#FACC15', borderRadius: '50%', animation: 'spin 1s linear infinite' },
  pLabel:     { fontSize: 12, fontWeight: 500, color: '#F8FAFC', margin: 0 },
  pSub:       { fontSize: 10, color: '#94A3B8', margin: 0 },
  pTrack:     { width: 260, height: 4, background: '#1E293B', borderRadius: 999, overflow: 'hidden' },
  pBar:       { height: '100%', background: '#FACC15', borderRadius: 999, transition: 'width 0.3s linear' },
  pPct:       { fontSize: 10, color: '#94A3B8', margin: 0 },
  iconCircleOk:   { width: 64, height: 64, borderRadius: '50%', background: 'rgba(110,231,183,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center' },
  iconCircleFail: { width: 64, height: 64, borderRadius: '50%', background: 'rgba(248,113,113,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center' },
  resTitle:   { fontSize: 15, fontWeight: 600, color: '#F8FAFC', margin: 0 },
  resSub:     { fontSize: 14, color: '#94A3B8', margin: 0 },
  infoBox:    { width: 320, background: '#1E293B', borderRadius: 16, padding: '14px 20px' },
  infoRow:    { display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0' },
  infoLbl:    { fontSize: 13, color: '#94A3B8' },
  infoVal:    { fontSize: 13, fontWeight: 500, color: '#F8FAFC' },
  roundBtn:   { background: 'rgba(148,163,184,0.6)', color: '#F8FAFC', border: 'none', borderRadius: 16, padding: '11px 28px', fontSize: 13, fontFamily: 'Inter, sans-serif', fontWeight: 500, cursor: 'pointer', marginTop: 4 },
  errBox:     { width: 240, background: '#1A0F0F', border: '1px solid #3D1515', borderRadius: 16, padding: '10px 14px' },
  errTxt:     { fontSize: 10, color: '#F43F5E', lineHeight: 1.7, margin: 0 },
};
