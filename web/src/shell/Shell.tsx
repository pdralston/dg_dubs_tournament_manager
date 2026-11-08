import { useState } from 'react';
import { Link, Outlet, useParams } from 'react-router-dom';
import { useAuth, type AppName } from '../auth/AuthContext';
import LoginModal from './LoginModal';

const APPS: AppName[] = ['dubs', 'tags', 'putt'];
const APP_LABEL: Record<AppName, string> = {
  dubs: 'Dubs',
  tags: 'Tags',
  putt: 'Putt',
};

// Shared chrome wrapping the org/app routes: brand, org/app switcher, and an
// auth/login state slot. Renders nested routes via <Outlet/>. The platform
// root (/) renders outside this shell (see router).
export default function Shell() {
  const { org, app } = useParams();
  const { isAuthenticated, identity, orgRole, isSuperuser, logout } = useAuth();
  const [showLogin, setShowLogin] = useState(false);

  return (
    <div className="dgr-shell">
      <header className="dgr-header">
        <div className="dgr-header-left">
          <Link to="/" className="dgr-brand">DG-Rater</Link>
          {org && (
            <>
              <span className="dgr-sep">/</span>
              <Link to={`/${org}`} className="dgr-org">{org}</Link>
            </>
          )}
        </div>

        {org && (
          <nav className="dgr-appswitch">
            {APPS.map((a) => (
              <Link
                key={a}
                to={`/${org}/${a}`}
                className={`dgr-app-tab${app === a ? ' is-active' : ''}`}
              >
                {APP_LABEL[a]}
              </Link>
            ))}
          </nav>
        )}

        <div className="dgr-header-right">
          {isAuthenticated ? (
            <>
              <span className="dgr-user">
                {identity?.username}
                {isSuperuser ? ' · site' : orgRole ? ` · ${orgRole}` : ''}
              </span>
              <button className="dgr-btn" onClick={() => logout()}>Log out</button>
            </>
          ) : (
            <button className="dgr-btn" onClick={() => setShowLogin(true)}>Log in</button>
          )}
        </div>
      </header>

      <div className="dgr-content">
        <Outlet />
      </div>

      {showLogin && <LoginModal onClose={() => setShowLogin(false)} />}
    </div>
  );
}
