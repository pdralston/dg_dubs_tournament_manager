import React, { useState, useEffect } from 'react';
import './App.css';

import './components/PlayerManager.css';
import './components/Leaderboard.css';
import './components/TournamentDirectory.css';
import './components/AcePotTracker.css';
import './components/TournamentCreation.css';
import './components/Admin.css';
import './components/AdminAudit.css';
import './components/LandingPage.css';

import LandingPage from './components/LandingPage';
import UnifiedTournamentView from './components/UnifiedTournamentView';
import TournamentDirectory from './components/TournamentDirectory';
import TournamentCreation from './components/TournamentCreation';
import PlayerManager from './components/PlayerManager';
import Leaderboard from './components/Leaderboard';
import AcePotTracker from './components/AcePotTracker';
import Admin from './components/Admin';
import AdminAudit from './components/AdminAudit';
import Login from './components/Login';
import { API_BASE_URL } from './config/api';

interface User {
  user_id: number;
  username: string;
  role: string;
}

function App() {
  const [activeTab, setActiveTab] = useState<'landing' | 'players' | 'leaderboard' | 'tournaments' | 'ace-pot' | 'admin'>('landing');
  const [selectedTournament, setSelectedTournament] = useState<number | null>(null);
  // 'current' = active (not-yet-archived) season; otherwise an archived season_id as string.
  // Lifted here (rather than inside TournamentDirectory) so the selection survives
  // navigating into a tournament and back via "Back to Tournaments".
  const [selectedSeason, setSelectedSeason] = useState<string>('current');
  const [tournamentMode, setTournamentMode] = useState<'view' | 'manage' | 'create'>('view');
  const [editingPendingId, setEditingPendingId] = useState<number | null>(null);
  const [playerManagerKey, setPlayerManagerKey] = useState(0);
  const [initialPlayerId, setInitialPlayerId] = useState<number | null>(null);
  const [user, setUser] = useState<User>({ user_id: 0, username: 'Viewer', role: 'Viewer' });
  const [showLogin, setShowLogin] = useState(false);

  const handleTournamentSelect = (tournamentId: number) => {
    setSelectedTournament(tournamentId);
    setTournamentMode('view');
  };

  const handleLogin = (userData: User) => {
    setUser(userData);
    setShowLogin(false);
  };

  const handleCancelLogin = () => {
    setShowLogin(false);
  };

  const handleLogout = async () => {
    try {
      await fetch(`${API_BASE_URL}/api/auth/logout`, {
        method: 'POST',
        credentials: 'include'
      });
    } catch (error) {
      console.error('Logout error:', error);
    }
    setUser({ user_id: 0, username: 'Viewer', role: 'Viewer' });
    setActiveTab('landing');
    setSelectedTournament(null);
    setSelectedSeason('current');
    setTournamentMode('view');
  };

  const canManageTournaments = () => user.role === 'Admin' || user.role === 'Director';

  const handleTournamentManage = (tournamentId: number) => {
    setSelectedTournament(tournamentId);
    setTournamentMode('manage');
  };

  const handleCreateTournament = () => {
    setSelectedTournament(null);
    setTournamentMode('create');
  };

  const handleBackToDirectory = () => {
    setSelectedTournament(null);
    setTournamentMode('view');
    setEditingPendingId(null);
  };

  const handleTournamentCreated = () => {
    setTournamentMode('view');
    setEditingPendingId(null);
  };

  const handleEditPending = (tournamentId: number) => {
    setEditingPendingId(tournamentId);
    setTournamentMode('create');
  };

  const renderHeader = () => (
    <header className="App-header">
      <h1>DG-Putt</h1>
      <nav>
        <button 
          className={activeTab === 'landing' ? 'active' : ''}
          onClick={() => setActiveTab('landing')}
        >
          HOME
        </button>
        <button 
          className={activeTab === 'players' ? 'active' : ''}
          onClick={() => {
            setInitialPlayerId(null);
            if (activeTab === 'players') {
              setPlayerManagerKey(prev => prev + 1);
            } else {
              setActiveTab('players');
            }
          }}
        >
          PLAYERS
        </button>
        <button 
          className={activeTab === 'leaderboard' ? 'active' : ''}
          onClick={() => setActiveTab('leaderboard')}
        >
          LEADERBOARD
        </button>
        <button 
          className={activeTab === 'tournaments' ? 'active' : ''}
          onClick={() => {
            setActiveTab('tournaments');
            setSelectedTournament(null);
            setSelectedSeason('current');
            setTournamentMode('view');
          }}
        >
          TOURNAMENTS
        </button>
        <button 
          className={activeTab === 'ace-pot' ? 'active' : ''}
          onClick={() => setActiveTab('ace-pot')}
        >
          ACE POT
        </button>
        {(user.role === 'Admin' || user.role === 'Director') && (
          <button 
            className={activeTab === 'admin' ? 'active' : ''}
            onClick={() => setActiveTab('admin')}
          >
            ADMIN
          </button>
        )}
        <div className="auth-section">
          {user.role === 'Viewer' ? (
            <button className="login-button" onClick={() => setShowLogin(true)}>
              Login
            </button>
          ) : (
            <>
              <button className="logout-button" onClick={handleLogout}>
                Logout
              </button>
              <span className="user-info">{user.username}</span>
            </>
          )}
        </div>
      </nav>
    </header>
  );

  if (activeTab === 'landing') {
    return (
      <div className="App">
        {showLogin && <Login onLogin={handleLogin} onCancel={handleCancelLogin} />}
        {renderHeader()}
        <LandingPage onNavigate={(tab) => setActiveTab(tab)} />
      </div>
    );
  }

  return (
    <div className="App">
      {showLogin && <Login onLogin={handleLogin} onCancel={handleCancelLogin} />}
      {renderHeader()}
      <main>
        {activeTab === 'players' && <PlayerManager key={playerManagerKey} userRole={user.role} initialPlayerId={initialPlayerId} />}
        {activeTab === 'leaderboard' && <Leaderboard onPlayerClick={(id) => { setInitialPlayerId(id); setPlayerManagerKey(k => k + 1); setActiveTab('players'); }} />}
        {activeTab === 'ace-pot' && <AcePotTracker />}
        {activeTab === 'admin' && (user.role === 'Admin' || user.role === 'Director') && (
          <Admin currentUser={user} />
        )}
        {activeTab === 'tournaments' && !selectedTournament && tournamentMode !== 'create' && (
          <TournamentDirectory 
            onTournamentSelect={handleTournamentSelect}
            onTournamentManage={handleTournamentManage}
            onCreateTournament={handleCreateTournament}
            onEditPending={handleEditPending}
            selectedSeason={selectedSeason}
            onSeasonChange={setSelectedSeason}
            userRole={user.role}
          />
        )}
        {activeTab === 'tournaments' && tournamentMode === 'create' && (
          <TournamentCreation
            onBack={handleBackToDirectory}
            onTournamentCreated={handleTournamentCreated}
            existingPendingId={editingPendingId}
          />
        )}
        {activeTab === 'tournaments' && selectedTournament && tournamentMode === 'view' && (
          <UnifiedTournamentView 
            tournamentId={selectedTournament} 
            onBack={handleBackToDirectory}
            showManagementActions={false}
          />
        )}
        {activeTab === 'tournaments' && selectedTournament && tournamentMode === 'manage' && (
          <UnifiedTournamentView 
            tournamentId={selectedTournament} 
            onBack={handleBackToDirectory}
            showManagementActions={true}
          />
        )}
      </main>
    </div>
  );
}

export default App;
