/**
 * DG-Tags app module, mounted by the unified shell at /:org/tags/*.
 *
 * Ported from the standalone DG-Tags SPA. Its former local AuthContext and
 * login modal are gone — auth is the shared shell + AuthContext. Role gating
 * maps onto the shared three-tier model:
 *   isDirector = hasAppRole('tags', 'director')   (admin satisfies this too)
 *   isAdmin    = hasAppRole('tags', 'admin')
 *
 * The data components (Standings/Events/Members/InventoryView) don't touch auth
 * directly, so they port verbatim; gating is all in this nav.
 */

import { useState, useEffect } from 'react';
import { useAuth } from '../../auth/AuthContext';
import Standings from './components/Standings';
import Events from './components/Events';
import Members from './components/Members';
import InventoryView from './components/InventoryView';
import './tags.css';

type View = 'standings' | 'events' | 'members' | 'inventory';

export default function TagsApp() {
  const { hasAppRole } = useAuth();
  const [activeView, setActiveView] = useState<View>('standings');

  const isDirector = hasAppRole('tags', 'director'); // admin satisfies this too
  const isAdmin = hasAppRole('tags', 'admin');

  const navItems: { key: View; label: string; requiresAuth?: boolean; requiresAdmin?: boolean }[] = [
    { key: 'standings', label: 'Standings' },
    { key: 'events', label: 'Events' },
    { key: 'members', label: 'Members', requiresAuth: true },
    { key: 'inventory', label: 'Inventory', requiresAdmin: true },
  ];

  const visibleNavItems = navItems.filter((item) => {
    if (item.requiresAdmin) return isAdmin;
    if (item.requiresAuth) return isDirector;
    return true;
  });

  // If the user loses access while on a gated view (e.g. logout), fall back to
  // the public standings so privileged content can't linger.
  useEffect(() => {
    if (activeView === 'inventory' && !isAdmin) setActiveView('standings');
    else if (activeView === 'members' && !isDirector) setActiveView('standings');
  }, [activeView, isAdmin, isDirector]);

  const renderView = () => {
    switch (activeView) {
      case 'standings':
        return <Standings />;
      case 'events':
        return <Events />;
      case 'members':
        // Defense in depth: never render gated views for an unauthorized user.
        return isDirector ? <Members /> : <Standings />;
      case 'inventory':
        return isAdmin ? <InventoryView /> : <Standings />;
    }
  };

  return (
    <div className="App">
      {/* DG-Tags' own app banner (title + nav). Auth controls removed — the
          shell owns login/logout. */}
      <header className="App-header">
        <h1>DG-Tags</h1>
        <nav>
          {visibleNavItems.map((item) => (
            <button
              key={item.key}
              className={activeView === item.key ? 'active' : ''}
              onClick={() => setActiveView(item.key)}
            >
              {item.label}
            </button>
          ))}
        </nav>
      </header>

      <main>{renderView()}</main>
    </div>
  );
}
