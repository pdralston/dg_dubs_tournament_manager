# Project Context — DG-Rater

Quick orientation for anyone (or future-you) picking this project up. For
detail, see `README.md` (setup/API) and
`docs/DG-Rater-2.0-Org-Governance-Design.md` (architecture & roadmap).

## What this is

A multi-app disc-golf platform under the **DG-Rater** umbrella, served by one
Flask backend on a single Elastic Beanstalk instance, backed by one shared
AWS RDS MySQL instance:

- **DG-Dubs** — doubles tournament rating system. Live at https://dg-rater.com.
- **DG-Tags** — bag-tag tracking. API live; standalone frontend still in dev.
- **DG-Putt** — putting league. Live at https://putt.dg-rater.com, currently a
  *separate* project/repo (`../puttingLeague/`) and EB env; consolidation into
  this backend is planned (design doc Phase 2), not yet done.

## Current state (as of 2026-10-07)

- **Org-level governance (Phase 1) is DEPLOYED to prod.** All domain data is
  scoped to an organization via an `org_id` column on tenant tables, with a
  `before_flush` hook that stamps org ownership on writes.
- **Org-Role Tier (design doc §13) scaffolding is IMPLEMENTED locally, not yet
  deployed to prod.** Authorization is now **two-axis**:
  - a per-app operational tier — `org_memberships` (roles: `admin` /
    `director`; one row per `(user, app)`, no wildcard);
  - an org-wide governance tier — `org_roles` (roles: `owner` / `manager`),
    which derives app-admin on every subscribed app;
  - plus a `users.is_superuser` platform bypass (cross-org).
  "Viewer" is **not** a stored role — it means *no membership* (public read).
- The single existing org is **Silicon Valley Disc Golf Club (SVDGC,
  `org_id=1`)**; all pre-existing data was backfilled to it.
- Schema is managed by **Alembic / Flask-Migrate** (migrations under
  `migrations/`; head `c3d4e5f6a7b8`). `db.create_all()` is only used for the
  SQLite test DB.
- The **URL direction** is path-based, org-first: `dg-rater.com/<org>/<app>`
  (e.g. `/svdgc/tags`). Not all frontends serve this yet.

## Layout

- `backend/app.py` — Flask app factory (`create_app`).
- `backend/models/` — SQLAlchemy models: `platform.py` (User, Org,
  OrgMembership, OrgRole, TenantMixin, sessions, PII log), `dubs.py`, `tags.py`.
- `backend/shared/` — `auth.py` (auth + `require_role` / `require_org_role`),
  `org_context.py` (resolve current org), `scoping.py` (org stamping/query
  helper).
- `backend/apps/dubs/`, `backend/apps/tags/` — per-app routes + services.
- `frontend/` (DG-Dubs SPA), `tags-frontend/` (DG-Tags SPA) — React + TS (CRA;
  migration to Vite planned).
- `migrations/` — Alembic migration chain.
- `tests/` — pytest suite (SQLite in-memory).

## Known follow-ups (see design doc §11a and §13 for the full list)

- **Deploy Org-Role Tier (§13) to prod.** The scaffolding + migration
  (`c3d4e5f6a7b8`) are implemented and rehearsed on a local MySQL dev DB, but
  not yet run against prod RDS. Run the §13.7 read-only pre-flight check first,
  then the usual snapshot-gated migrate-then-deploy.
- **Set `users.is_superuser` on the site-owner account.** The platform bypass
  is honored throughout the auth layer, but the flag defaults to false, so the
  prod admin is currently org `owner` of SVDGC (equivalent while single-org),
  not a cross-org platform superuser. It's a manual DB flag until an admin
  portal exposes user management (§13.8).
- **Governance endpoints (`/api/org/*`) + entitlements are not built.**
  `require_org_role` exists but is attached to nothing; `subscribed_apps()` is
  a stub returning all apps (§13.8).
- Optional hardening: prod DB secrets are plaintext EB env vars (readable by
  anyone with EB/CFN read on the account). Moving them to SSM/Secrets Manager
  is a low-priority nice-to-have, not urgent for a solo project. (Command-line
  exposure during the deploy was on a private machine — not a concern.)
- In-memory `TournamentRatingSystem` (DG-Dubs read cache) is single-org; must
  be made per-org before onboarding a 2nd org.
- Migrate tenant read call-sites to org-scoped queries when multi-org lands.
- CRA → Vite before the path-based frontend deploy.
- Phase 2: fold DG-Putt into this backend (rename its tables `putt_*`).
