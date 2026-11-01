import { useEffect, useState } from 'react';
import { Navigate, Route, Routes, useLocation } from 'react-router-dom';
import { Check, Crown } from 'lucide-react';
import AuthPage from './pages/AuthPage.jsx';
import Dashboard from './pages/Dashboard.jsx';
import ExecutiveIdentity from './pages/ExecutiveIdentity.jsx';
import IntelligentInbox from './pages/IntelligentInbox.jsx';
import AIReplyStudio from './pages/AIReplyStudio.jsx';
import DailyBriefing from './pages/DailyBriefing.jsx';
import Settings from './pages/Settings.jsx';
import Sidebar from './components/Sidebar.jsx';
import Header from './components/Header.jsx';
import { apiRequest } from './lib/api.js';
import { defaultPreferences, defaultProfile } from './data/profile.js';

function LoadingScreen({ message }) {
  return <main className="auth-loading"><span><Crown size={23} /></span><p>{message}</p></main>;
}

export default function App() {
  const [user, setUser] = useState(null);
  const [account, setAccount] = useState({ profile: {}, preferences: {} });
  const [status, setStatus] = useState('loading');
  const [error, setError] = useState('');

  async function authenticate(authenticatedUser) {
    const data = await apiRequest('/api/account');
    setUser(authenticatedUser);
    setAccount(data);
    setStatus('authenticated');
  }

  useEffect(() => {
    let active = true;
    async function restoreSession() {
      try {
        const { user: currentUser } = await apiRequest('/api/auth/me');
        const data = await apiRequest('/api/account');
        if (active) {
          setUser(currentUser);
          setAccount(data);
          setStatus('authenticated');
        }
      } catch (loadError) {
        if (!active) return;
        if (loadError.message === 'Please log in to continue.' || loadError.message.includes('session has expired')) {
          setStatus('signed-out');
        } else {
          setError(loadError.message);
          setStatus('error');
        }
      }
    }
    restoreSession();
    return () => { active = false; };
  }, []);

  async function logout() {
    try {
      await apiRequest('/api/auth/logout', { method: 'POST' });
    } finally {
      setUser(null);
      setAccount({ profile: {}, preferences: {} });
      setStatus('signed-out');
      window.location.assign('/login');
    }
  }

  if (status === 'loading') return <LoadingScreen message="Opening your private office..." />;
  if (status === 'error') {
    return <main className="auth-loading"><div className="eyebrow">PRIVATE OFFICE UNAVAILABLE</div><h1>We could not reach the API.</h1><p>{error}</p><button className="auth-submit" onClick={() => window.location.reload()}>Try again</button></main>;
  }

  if (status === 'signed-out') {
    return (
      <Routes>
        <Route path="/register" element={<AuthPage mode="register" onSuccess={authenticate} />} />
        <Route path="*" element={<AuthPage mode="login" onSuccess={authenticate} />} />
      </Routes>
    );
  }

  return (
    <Routes>
      <Route path="/login" element={<Navigate to="/" replace />} />
      <Route path="/register" element={<Navigate to="/" replace />} />
      <Route path="*" element={<Workspace user={user} account={account} onAccountChange={setAccount} onLogout={logout} />} />
    </Routes>
  );
}

function Workspace({ user, account, onAccountChange, onLogout }) {
  const [profile, setProfile] = useState(() => ({ ...defaultProfile, ...account.profile }));
  const [preferences, setPreferences] = useState(() => ({ ...defaultPreferences, ...account.preferences }));
  const [toast, setToast] = useState('');
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [selectedEmail, setSelectedEmail] = useState(null);
  const location = useLocation();

  function showToast(message) {
    setToast(message);
    window.setTimeout(() => setToast(''), 2600);
  }

  async function saveProfile(nextProfile) {
    try {
      const updated = await apiRequest('/api/account', { method: 'PATCH', body: JSON.stringify({ profile: nextProfile }) });
      setProfile(nextProfile);
      onAccountChange(updated);
      showToast('Executive profile saved');
    } catch (saveError) {
      showToast(saveError.message);
    }
  }

  async function savePreferences(nextPreferences) {
    try {
      const updated = await apiRequest('/api/account', { method: 'PATCH', body: JSON.stringify({ preferences: nextPreferences }) });
      setPreferences(nextPreferences);
      onAccountChange(updated);
    } catch (saveError) {
      showToast(saveError.message);
    }
  }

  return (
    <div className="app-shell">
      <Sidebar profile={profile} onLogout={onLogout} open={mobileNavOpen} onClose={() => setMobileNavOpen(false)} />
      <main className="main-area">
        <Header user={user} onMenu={() => setMobileNavOpen(true)} />
        <div className="page-wrap">
          <Routes>
            <Route path="/" element={<Dashboard profile={profile} onSelectEmail={setSelectedEmail} />} />
            <Route path="/identity" element={<ExecutiveIdentity profile={profile} onSave={saveProfile} />} />
            <Route path="/inbox" element={<IntelligentInbox selectedEmail={selectedEmail} onSelectEmail={setSelectedEmail} />} />
            <Route path="/studio" element={<AIReplyStudio selectedEmail={selectedEmail} onSelectEmail={setSelectedEmail} onToast={showToast} />} />
            <Route path="/briefing" element={<DailyBriefing preferences={preferences} onChange={savePreferences} onToast={showToast} />} />
            <Route path="/settings" element={<Settings profile={profile} preferences={preferences} onSaveProfile={saveProfile} onChangePreferences={savePreferences} onToast={showToast} />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </div>
      </main>
      {toast && <div className="toast"><Check size={16} />{toast}</div>}
      <span className="route-marker" aria-hidden="true">{location.pathname}</span>
    </div>
  );
}
