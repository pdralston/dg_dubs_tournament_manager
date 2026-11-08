import { Link } from 'react-router-dom';

// Platform root (/). Placeholder for the future tabbed DG-Rater intro +
// organization directory. For now: a short intro and the single-org ingress
// (SVDGC). Per-org landing pages live at /:org.
export default function PlatformLanding() {
  const orgs = [{ slug: 'svdgc', name: 'Silicon Valley Disc Golf Club' }];

  return (
    <main className="dgr-page">
      <h1>DG-Rater</h1>
      <p className="dgr-lede">
        A multi-app disc golf platform — doubles ratings, bag-tag tracking, and
        putting leagues — under one roof.
      </p>

      <section>
        <h2>Organizations</h2>
        <ul className="dgr-card-grid">
          {orgs.map((o) => (
            <li key={o.slug} className="dgr-card">
              <Link to={`/${o.slug}`}>
                <span className="dgr-card-title">{o.name}</span>
                <span className="dgr-card-sub">/{o.slug}</span>
              </Link>
            </li>
          ))}
        </ul>
      </section>

      <p className="dgr-note">
        Placeholder — a richer intro + organization directory is a later
        feature.
      </p>
    </main>
  );
}
