import { useState, useEffect, useCallback } from 'react';
import Sidebar from './components/Sidebar';
import Topbar from './components/Topbar';
import Footer from './components/Footer';
import Dashboard from './pages/Dashboard';
import Report from './pages/Report';
import Profiling from './pages/Profiling';
import Upload from './pages/Upload';
import client from './api/client';

export default function App() {
  const [activePage, setActivePage] = useState('dashboard');
  const [trades, setTrades]     = useState([]);
  const [analysis, setAnalysis] = useState([]);
  const [uploads, setUploads]   = useState([]);

  const refetch = useCallback(async () => {
    try {
      const [tRes, aRes, uRes] = await Promise.all([
        client.get('/trades/'),
        client.get('/analysis/'),
        client.get('/trades/uploads'),
      ]);
      setTrades(tRes.data || []);
      setAnalysis(aRes.data || []);
      setUploads(uRes.data || []);
    } catch (e) {
      console.error('데이터 로딩 실패:', e);
    }
  }, []);

  useEffect(() => { refetch(); }, [refetch]);

  const lastUploadDate = (() => {
    if (!trades.length) return null;
    const sorted = [...trades].sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
    return sorted[0].created_at?.slice(0, 10)?.replace(/-/g, '/');
  })();

  const renderPage = () => {
    switch (activePage) {
      case 'dashboard': return <Dashboard trades={trades} analysis={analysis} onNavigate={setActivePage} />;
      case 'report':    return <Report trades={trades} analysis={analysis} />;
      case 'profiling': return <Profiling />;
      case 'upload':    return <Upload onNavigate={setActivePage} onComplete={refetch} trades={trades} uploads={uploads} />;
      default:          return <Dashboard trades={trades} analysis={analysis} onNavigate={setActivePage} />;
    }
  };

  return (
    <div style={styles.root}>
      <Sidebar activePage={activePage} onNavigate={setActivePage} />
      <div style={styles.main}>
        <Topbar activePage={activePage} lastUploadDate={lastUploadDate} />
        <div style={styles.content}>
          <div style={{ flex: 1 }}>
            {renderPage()}
          </div>
          <Footer />
        </div>
      </div>
    </div>
  );
}

const styles = {
  root: {
    display: 'flex',
    height: '100vh',
    overflow: 'hidden',
  },
  main: {
    position: 'fixed',
    left: 240,
    right: 0,
    top: 0,
    bottom: 0,
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
  },
  content: {
    flex: 1,
    overflowY: 'auto',
    overflowX: 'auto',
    display: 'flex',
    flexDirection: 'column',
  },
};
