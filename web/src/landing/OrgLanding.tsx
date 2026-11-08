import { Link, useParams } from 'react-router-dom';
import type { AppName } from '../auth/AuthContext';

// Org root (/:org). Placeholder for a per-org landing page. For now: lists the
// org's apps as ingresses into /:org/:app. Each org will get its own fleshed-out
// page in a later feature.
const APPS: { key: AppName; name: string; blurb: string }[] = [
  { key: 'dubs', name: 'DG-Dubs', blurb: 'Doubles tournament ratings' },
  { key: 'tags', name: 'DG-Tags', blurb: 'Bag-tag tracking' },
  { key: 'putt', name: 'DG-Putt', blurb: 'Putting league brackets' },
];

// Phase 1 is single-org; only svdgc is known. Unknown slugs still render the
// placeholder (org validation lands with multi-org support).
const KNOWN_ORGS: Record<string, string> = {
  svdgc: 'Silicon Valley Disc Golf Club',
};

export default function OrgLanding() {
  const { org = '' } = useParams();
  const orgName = KNOWN_ORGS[org] ?? org;

  return (
    <main className="dgr-page">
      <nav className="dgr-crumbs">
        <Link to="/">DG-Rater</Link> <span>/</span> <span>{org}</span>
      </nav>
      <h1>{orgName}</h1>

      <section>
        <h2>Apps</h2>
        <ul className="dgr-card-grid">
          {APPS.map((a) => (
            <li key={a.key} className="dgr-card">
              <Link to={`/${org}/${a.key}`}>
                <span className="dgr-card-title">{a.name}</span>
                <span className="dgr-card-sub">{a.blurb}</span>
              </Link>
            </li>
          ))}
        </ul>
      </section>

      <p className="dgr-note">Placeholder — per-org landing is a later feature.</p>
    </main>
  );
}
