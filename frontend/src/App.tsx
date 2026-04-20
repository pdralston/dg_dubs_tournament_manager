import React, { useState, useEffect } from 'react';
import './App.css';
import Login from './components/Login';
import PlayerList from './components/PlayerList';
import PlayerDetails from './components/PlayerDetails';
import Tournaments from './components/Tournaments';
import AcePotTracker from './components/AcePotTracker';
import Admin from './components/Admin';
import { API_BASE_URL } from './config/api';
import { User } from './types';

type Tab = 'players' | 'tournaments' | 'ace-pot' | 'admin';

function App() {
  const [activeTab, setActiveTab] = useState<Tab>('players');
  const [user, setUser] = useState<User>({ user_id: 0, username: 'Viewer', role: 'Viewer' });
  const [showLogin, setShowLogin] = useState(false);
  const [selectedPlayer, setSelectedPlayer] = useState<string | null>(null);

  useEffect(() => {
    const checkSession = async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/api/auth/me`, { credentials: 'include' });
        if (res.ok) {
          const data = await res.json();
          if (data.user_id && data.user_id !== 0) setUser(data);
        }
      } catch {}
    };
    checkSession();
  }, []);

  const handleLogin = (userData: User) => { setUser(userData); setShowLogin(false); };

  const handleLogout = async () => {
    try { await fetch(`${API_BASE_URL}/api/auth/logout`, { method: 'POST', credentials: 'include' }); } catch {}
    setUser({ user_id: 0, username: 'Viewer', role: 'Viewer' });
    setActiveTab('players');
  };

  const navigateTo = (tab: Tab) => { setActiveTab(tab); setSelectedPlayer(null); };

  const renderContent = () => {
    if (selectedPlayer) return <PlayerDetails playerName={selectedPlayer} onBack={() => setSelectedPlayer(null)} />;
    switch (activeTab) {
      case 'players': return <PlayerList userRole={user.role} onPlayerSelect={setSelectedPlayer} />;
      case 'tournaments': return <Tournaments userRole={user.role} />;
      case 'ace-pot': return <AcePotTracker userRole={user.role} />;
      case 'admin': return <Admin currentUser={user} onUserUpdated={setUser} />;
    }
  };

  const navTabs: { key: Tab; label: string; authRequired?: boolean }[] = [
    { key: 'players', label: 'PLAYERS' },
    { key: 'tournaments', label: 'TOURNAMENTS' },
    { key: 'ace-pot', label: 'ACE POT' },
    { key: 'admin', label: user.role === 'admin' ? 'ADMIN' : 'PROFILE', authRequired: true },
  ];

  return (
    <div className="App">
      {showLogin && <Login onLogin={handleLogin} onCancel={() => setShowLogin(false)} />}
      <header className="App-header">
        <h1>DG-Dubs</h1>
        <nav>
          {navTabs
            .filter(t => !t.authRequired || (user.role === 'admin' || user.role === 'director'))
            .map(t => (
              <button key={t.key} className={activeTab === t.key && !selectedPlayer ? 'active' : ''} onClick={() => navigateTo(t.key)}>
                {t.label}
              </button>
            ))}
          <div className="auth-section">
            {user.role === 'Viewer' ? (
              <button className="login-button" onClick={() => setShowLogin(true)}>Login</button>
            ) : (
              <>
                <button className="logout-button" onClick={handleLogout}>Logout</button>
                <span className="user-info">{user.username}</span>
              </>
            )}
          </div>
        </nav>
      </header>
      <main>{renderContent()}</main>
    </div>
  );
}

export default App;
