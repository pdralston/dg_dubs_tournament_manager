import { useParams, Navigate } from 'react-router-dom';
import type { AppName } from '../auth/AuthContext';
import DubsApp from '../apps/dubs/DubsApp';
import TagsApp from '../apps/tags/TagsApp';
import PuttApp from '../apps/putt/PuttApp';

// Mounts the app addressed by the /:org/:app/* route. Each app renders inside a
// `data-app` container so per-app styles (ported in later) can be scoped under
// it (e.g. `[data-app="dubs"] .foo`), preventing global CSS collisions between
// the three apps now sharing one DOM.
const APPS: Record<AppName, React.ComponentType> = {
  dubs: DubsApp,
  tags: TagsApp,
  putt: PuttApp,
};

export default function AppHost() {
  const { org = '', app = '' } = useParams();
  const Comp = APPS[app as AppName];

  // Unknown app segment -> bounce to the org landing.
  if (!Comp) return <Navigate to={`/${org}`} replace />;

  return (
    <div className="dgr-app-host" data-app={app}>
      <Comp />
    </div>
  );
}
