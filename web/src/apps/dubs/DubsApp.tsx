/**
 * DG-Dubs app module, mounted by the unified shell at /:org/dubs/*.
 *
 * Ported from the standalone DG-Dubs SPA. The app's former responsibilities for
 * auth, the top-level header, and the login modal are GONE — those belong to
 * the shared shell + AuthContext now. This module keeps only DG-Dubs' own
 * content: the players / tournaments / ace-pot / admin tabs and the player
 * drill-down.
 *
 * Role gating uses the shared three-tier context: `appRole('dubs')` yields
 * 'admin' | 'director' | null (null = viewer), resolved the same way the
 * backend enforces it. The ported child components still take a `userRole`
 * string and check `=== 'admin' || 'director'`, so we pass appRole through.
 *
 * Styling: renders inside `.App` (so the ported `.App*`-scoped CSS applies)
 * within the shell's `[data-app="dubs"]` host.
 */

import { useState, useEffect } from 'react';
import { useAuth } from '../../auth/AuthContext';
import PlayerList from './components/PlayerList';
import PlayerDetails from './components/PlayerDetails';
import Tournaments from './components/Tournaments';
import AcePotTracker from './components/AcePotTracker';
import Admin from './components/Admin';
import type { User } from './types';
import './styles/theme.css';
import './dubs.css';

type Tab = 'players' | 'tournaments' | 'ace-pot' | 'admin';

export default function DubsApp() {
  const { identity, appRole, refresh } = useAuth();
  const [activeTab, setActiveTab] = useState<Tab>('players');
  const [selectedPlayer, setSelectedPlayer] = useState<string | null>(null);

  // Effective DG-Dubs role for the current user (null -> 'Viewer' for the
  // string-prop API the ported components expect).
  const role = appRole('dubs') ?? 'Viewer';
  const canOperate = role === 'admin' || role === 'director';

  // If the user loses operate access while on the admin tab (e.g. logout),
  // fall back to the public players tab so admin content can't linger.
  useEffect(() => {
    if (activeTab === 'admin' && !canOperate) {
      setActiveTab('players');
      setSelectedPlayer(null);
    }
  }, [activeTab, canOperate]);

  // Shape the shared identity into the User object Admin.tsx expects.
  const currentUser: User = {
    user_id: identity?.user_id ?? 0,
    username: identity?.username ?? 'Viewer',
    role,
  };

  const navigateTo = (tab: Tab) => {
    setActiveTab(tab);
    setSelectedPlayer(null);
  };

  const renderContent = () => {
    if (selectedPlayer) {
      return (
        <PlayerDetails
          playerName={selectedPlayer}
          onBack={() => setSelectedPlayer(null)}
        />
      );
    }
    switch (activeTab) {
      case 'players':
        return <PlayerList userRole={role} onPlayerSelect={setSelectedPlayer} />;
      case 'tournaments':
        return <Tournaments userRole={role} />;
      case 'ace-pot':
        return <AcePotTracker userRole={role} />;
      case 'admin':
        // Defense in depth: never render admin content for a non-operator,
        // even for a render before the reset effect runs.
        if (!canOperate) {
          return <PlayerList userRole={role} onPlayerSelect={setSelectedPlayer} />;
        }
        // onUserUpdated re-syncs the shared auth identity after a profile edit.
        return <Admin currentUser={currentUser} onUserUpdated={() => refresh()} />;
    }
  };

  const tabs: { key: Tab; label: string; authRequired?: boolean }[] = [
    { key: 'players', label: 'PLAYERS' },
    { key: 'tournaments', label: 'TOURNAMENTS' },
    { key: 'ace-pot', label: 'ACE POT' },
    { key: 'admin', label: role === 'admin' ? 'ADMIN' : 'PROFILE', authRequired: true },
  ];

  return (
    <div className="App">
      {/* DG-Dubs' own app-level header (title + nav). The platform brand/login
          lives in the unified shell above this; the app keeps its own banner to
          delineate app scope. Auth controls were removed (shell owns them). */}
      <header className="App-header">
        <h1>DG-Dubs</h1>
        <nav>
          {tabs
            .filter((t) => !t.authRequired || canOperate)
            .map((t) => (
              <button
                key={t.key}
                className={activeTab === t.key && !selectedPlayer ? 'active' : ''}
                onClick={() => navigateTo(t.key)}
              >
                {t.label}
              </button>
            ))}
        </nav>
      </header>
      <main>{renderContent()}</main>
    </div>
  );
}
