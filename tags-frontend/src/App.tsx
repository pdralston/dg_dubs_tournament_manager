import React, { useState } from 'react';
import './App.css';
import { AuthProvider, useAuth } from './context/AuthContext';
import Login from './components/Login';
import Standings from './components/Standings';
import Events from './components/Events';
import Members from './components/Members';
import InventoryView from './components/InventoryView';

type View = 'standings' | 'events' | 'members' | 'inventory';

function AppContent() {
  const { user, isAuthenticated, isAdmin, isDirector, logout } = useAuth();
  const [activeView, setActiveView] = useState<View>('standings');
  const [showLogin, setShowLogin] = useState(false);

  const navItems: { key: View; label: string; requiresAuth?: boolean; requiresAdmin?: boolean }[] = [
    { key: 'standings', label: 'Standings' },
    { key: 'events', label: 'Events' },
    { key: 'members', label: 'Members', requiresAuth: true },
    { key: 'inventory', label: 'Inventory', requiresAdmin: true },
  ];

  const visibleNavItems = navItems.filter(item => {
    if (item.requiresAdmin) return isAdmin;
    if (item.requiresAuth) return isDirector;
    return true;
  });

  const renderView = () => {
    switch (activeView) {
      case 'standings': return <Standings />;
      case 'events': return <Events />;
      case 'members': return <Members />;
      case 'inventory': return <InventoryView />;
    }
  };

  return (
    <div className="App">
      {showLogin && <Login onClose={() => setShowLogin(false)} />}

      <header className="App-header">
        <h1>DG-Tags</h1>
        <nav>
          {visibleNavItems.map(item => (
            <button
              key={item.key}
              className={activeView === item.key ? 'active' : ''}
              onClick={() => setActiveView(item.key)}
            >
              {item.label}
            </button>
          ))}
          <div className="auth-section">
            {!isAuthenticated ? (
              <button className="login-button" onClick={() => setShowLogin(true)}>Login</button>
            ) : (
              <>
                <button className="logout-button" onClick={logout}>Logout</button>
                <span className="user-info">{user.username}</span>
              </>
            )}
          </div>
        </nav>
      </header>

      <main>{renderView()}</main>
    </div>
  );
}

function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

export default App;
