import { LayoutDashboard, FileText, Brain, ChevronRight, Upload } from 'lucide-react';
import { ReactComponent as Logo } from '../logo3.svg';

const menuItems = [
  { id: 'dashboard', label: '대시보드', icon: LayoutDashboard },
  { id: 'report', label: '매매 리포트', icon: FileText },
  { id: 'profiling', label: '성향 프로파일링', icon: Brain },
];

export default function Sidebar({ activePage, onNavigate }) {
  return (
    <aside style={styles.sidebar}>
      <div style={styles.logoArea}>
        <Logo style={styles.logoSvg} />
      </div>

      <nav style={styles.nav}>
        {menuItems.map(({ id, label, icon: Icon }) => {
          const active = activePage === id;
          return (
            <button
              key={id}
              onClick={() => onNavigate(id)}
              style={{
                ...styles.menuItem,
                ...(active ? styles.menuItemActive : {}),
              }}
            >
              <Icon size={18} style={styles.menuIcon} />
              <span>{label}</span>
              {active && <ChevronRight size={16} style={styles.chevron} />}
            </button>
          );
        })}
      </nav>

      <div style={styles.bottom}>
        <button style={styles.uploadBtn} onClick={() => onNavigate('upload')}>
          <Upload size={16} style={{ marginRight: 8 }} />
          매매내역 업로드
        </button>
      </div>
    </aside>
  );
}

const styles = {
  sidebar: {
    width: 240,
    minWidth: 240,
    height: '100vh',
    background: '#0F172A',
    display: 'flex',
    flexDirection: 'column',
    borderRight: '1px solid #1E293B',
    position: 'fixed',
    left: 0,
    top: 0,
  },
  logoArea: {
    padding: '24px 20px 20px',
  },
  logoSvg: {
    width: '100%',
    height: 'auto',
    maxHeight: 32,
    display: 'block',
  },
  nav: {
    flex: 1,
    padding: '16px 12px',
    display: 'flex',
    flexDirection: 'column',
    gap: 4,
  },
  menuItem: {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
    padding: '10px 12px',
    borderRadius: 10,
    border: 'none',
    background: 'transparent',
    color: '#F8FAFC',
    fontSize: 14,
    fontFamily: 'Inter, sans-serif',
    cursor: 'pointer',
    width: '100%',
    textAlign: 'left',
    transition: 'background 0.15s',
  },
  menuItemActive: {
    background: '#1E293B',
  },
  menuIcon: {
    flexShrink: 0,
  },
  chevron: {
    marginLeft: 'auto',
    color: '#94A3B8',
  },
  bottom: {
    padding: '16px 12px 20px',
    display: 'flex',
    flexDirection: 'column',
  },
  uploadBtn: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '12px 16px',
    borderRadius: 12,
    border: 'none',
    background: 'rgba(148, 163, 184, 0.6)',
    color: '#F8FAFC',
    fontSize: 14,
    fontFamily: 'Inter, sans-serif',
    fontWeight: 500,
    cursor: 'pointer',
    width: '100%',
  },
};
