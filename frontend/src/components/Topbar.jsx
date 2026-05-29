import { Bell, User, Calendar, LayoutDashboard, FileText, Brain, Upload } from 'lucide-react';

const pageInfo = {
  dashboard: { title: '대시보드',      icon: LayoutDashboard },
  report:    { title: '매매 리포트',    icon: FileText },
  profiling: { title: '성향 프로파일링', icon: Brain },
  upload:    { title: '매매내역 업로드', icon: Upload },
};

export default function Topbar({ activePage, lastUploadDate }) {
  const { title, icon: PageIcon } = pageInfo[activePage] ?? pageInfo.dashboard;

  return (
    <header style={styles.topbar}>
      <div style={styles.titleRow}>
        <PageIcon size={18} color="#F8FAFC" style={{ flexShrink: 0 }} />
        <h1 style={styles.title}>{title}</h1>
      </div>
      <div style={styles.right}>
        <div style={styles.dateChip}>
          <Calendar size={14} style={{ marginRight: 6, color: '#94A3B8' }} />
          <span style={styles.dateLabel}>최근 업로드:</span>
          <span style={styles.dateValue}>{lastUploadDate ?? '-'}</span>
        </div>
        <div style={styles.iconBtn}>
          <Bell size={18} />
          <span style={styles.badge}>12</span>
        </div>
        <div style={styles.iconBtn}>
          <User size={18} />
        </div>
      </div>
    </header>
  );
}

const styles = {
  topbar: {
    height: 60,
    flexShrink: 0,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '0 28px',
    borderBottom: '1px solid #1E293B',
    background: '#0F172A',
  },
  titleRow: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
  },
  title: {
    fontSize: 16,
    fontWeight: 600,
    color: '#F8FAFC',
  },
  right: {
    display: 'flex',
    alignItems: 'center',
    gap: 16,
  },
  dateChip: {
    display: 'flex',
    alignItems: 'center',
    fontSize: 13,
    color: '#94A3B8',
  },
  dateLabel: {
    marginRight: 4,
  },
  dateValue: {
    color: '#F8FAFC',
    fontWeight: 500,
  },
  iconBtn: {
    position: 'relative',
    width: 36,
    height: 36,
    borderRadius: 10,
    background: '#1E293B',
    border: 'none',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: '#F8FAFC',
    cursor: 'pointer',
  },
  badge: {
    position: 'absolute',
    top: -4,
    right: -4,
    background: '#F43F5E',
    color: '#fff',
    fontSize: 10,
    fontWeight: 700,
    borderRadius: 999,
    minWidth: 16,
    height: 16,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '0 3px',
    fontFamily: 'Inter, sans-serif',
  },
};
