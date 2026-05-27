import { useState } from 'react';
import Sidebar from './components/Sidebar';
import Topbar from './components/Topbar';
import Footer from './components/Footer';
import Dashboard from './pages/Dashboard';
import Report from './pages/Report';
import Profiling from './pages/Profiling';
import Upload from './pages/Upload';

export default function App() {
  const [activePage, setActivePage] = useState('dashboard');

  const renderPage = () => {
    switch (activePage) {
      case 'dashboard': return <Dashboard onNavigate={setActivePage} />;
      case 'report':    return <Report />;
      case 'profiling': return <Profiling />;
      case 'upload':    return <Upload onNavigate={setActivePage} />;
      default:          return <Dashboard onNavigate={setActivePage} />;
    }
  };

  return (
    <div style={styles.root}>
      <Sidebar activePage={activePage} onNavigate={setActivePage} />
      <div style={styles.main}>
        <Topbar activePage={activePage} />
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
