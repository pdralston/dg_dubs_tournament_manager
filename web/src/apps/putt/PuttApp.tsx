/**
 * DG-Putt app module, mounted by the unified shell at /:org/putt/*.
 *
 * Ported from the standalone DG-Putt SPA (the richest app: brackets, live
 * Socket.IO updates, tournament lifecycle). Its former own auth/login/logout
 * are removed — auth is the shared shell + AuthContext. Everything else (the
 * landing, the tournament/season/mode state machine, the player-manager remount
 * key) is preserved.
 *
 * Role casing bridge: the ported components compare against DG-Putt's
 * capitalized role strings ('Admin' | 'Director' | 'Viewer'), but the shared
 * context yields lowercase 'admin' | 'director' | null. We derive a capitalized
 * `puttRole` so every existing `=== 'Admin'` / `=== 'Director'` check keeps
 * working unchanged.
 *
 * API calls already target /api/putt/* (repointed during the earlier fold-in);
 * Socket.IO connects to API_BASE_URL and the dev server proxies /socket.io.
 */

import { useState, useEffect } from 'react';
import { useAuth } from '../../auth/AuthContext';

import './styles/theme.css';
import './putt.css';
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

type Tab = 'landing' | 'players' | 'leaderboard' | 'tournaments' | 'ace-pot' | 'admin';

export default function PuttApp() {
  const { identity, appRole } = useAuth();

  // Bridge shared lowercase role -> DG-Putt's capitalized strings.
  const effective = appRole('putt'); // 'admin' | 'director' | null
  const puttRole = effective === 'admin' ? 'Admin' : effective === 'director' ? 'Director' : 'Viewer';
  const canManage = puttRole === 'Admin' || puttRole === 'Director';

  const currentUser = {
    user_id: identity?.user_id ?? 0,
    username: identity?.username ?? 'Viewer',
    role: puttRole,
  };

  const [activeTab, setActiveTab] = useState<Tab>('landing');
  const [selectedTournament, setSelectedTournament] = useState<number | null>(null);
  const [selectedSeason, setSelectedSeason] = useState<string>('current');
  const [tournamentMode, setTournamentMode] = useState<'view' | 'manage' | 'create'>('view');
  const [editingPendingId, setEditingPendingId] = useState<number | null>(null);
  const [playerManagerKey, setPlayerManagerKey] = useState(0);
  const [initialPlayerId, setInitialPlayerId] = useState<number | null>(null);

  // appRole-loss reset guard: if the user loses manage access while on the
  // admin tab (e.g. logout), fall back to the public landing.
  useEffect(() => {
    if (activeTab === 'admin' && !canManage) {
      setActiveTab('landing');
      setSelectedTournament(null);
      setTournamentMode('view');
    }
  }, [activeTab, canManage]);

  const handleTournamentSelect = (tournamentId: number) => {
    setSelectedTournament(tournamentId);
    setTournamentMode('view');
  };
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
        <button className={activeTab === 'landing' ? 'active' : ''} onClick={() => setActiveTab('landing')}>
          HOME
        </button>
        <button
          className={activeTab === 'players' ? 'active' : ''}
          onClick={() => {
            setInitialPlayerId(null);
            if (activeTab === 'players') setPlayerManagerKey((prev) => prev + 1);
            else setActiveTab('players');
          }}
        >
          PLAYERS
        </button>
        <button className={activeTab === 'leaderboard' ? 'active' : ''} onClick={() => setActiveTab('leaderboard')}>
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
        <button className={activeTab === 'ace-pot' ? 'active' : ''} onClick={() => setActiveTab('ace-pot')}>
          ACE POT
        </button>
        {canManage && (
          <button className={activeTab === 'admin' ? 'active' : ''} onClick={() => setActiveTab('admin')}>
            ADMIN
          </button>
        )}
      </nav>
    </header>
  );

  if (activeTab === 'landing') {
    return (
      <div className="App">
        {renderHeader()}
        <LandingPage onNavigate={(tab) => setActiveTab(tab as Tab)} />
      </div>
    );
  }

  return (
    <div className="App">
      {renderHeader()}
      <main>
        {activeTab === 'players' && (
          <PlayerManager key={playerManagerKey} userRole={puttRole} initialPlayerId={initialPlayerId} />
        )}
        {activeTab === 'leaderboard' && (
          <Leaderboard
            onPlayerClick={(id) => {
              setInitialPlayerId(id);
              setPlayerManagerKey((k) => k + 1);
              setActiveTab('players');
            }}
          />
        )}
        {activeTab === 'ace-pot' && <AcePotTracker />}
        {activeTab === 'admin' && canManage && <Admin currentUser={currentUser} />}
        {activeTab === 'tournaments' && !selectedTournament && tournamentMode !== 'create' && (
          <TournamentDirectory
            onTournamentSelect={handleTournamentSelect}
            onTournamentManage={handleTournamentManage}
            onCreateTournament={handleCreateTournament}
            onEditPending={handleEditPending}
            selectedSeason={selectedSeason}
            onSeasonChange={setSelectedSeason}
            userRole={puttRole}
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
