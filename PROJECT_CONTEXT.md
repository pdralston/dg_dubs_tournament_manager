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

## Current state (as of 2026-09-27)

- **Org-level governance (Phase 1) is DEPLOYED to prod.** All domain data is
  scoped to an organization via an `org_id` column on tenant tables, with a
  `before_flush` hook that stamps org ownership on writes. Authorization is
  per-org / per-app via `org_memberships` (roles: admin / director / viewer;
  plus a `users.is_superuser` platform bypass).
- The single existing org is **Silicon Valley Disc Golf Club (SVDGC,
  `org_id=1`)**; all pre-existing data was backfilled to it.
- Schema is managed by **Alembic / Flask-Migrate** (migrations under
  `migrations/`). `db.create_all()` is only used for the SQLite test DB.
- The **URL direction** is path-based, org-first: `dg-rater.com/<org>/<app>`
  (e.g. `/svdgc/tags`). Not all frontends serve this yet.

## Layout

- `backend/app.py` — Flask app factory (`create_app`).
- `backend/models/` — SQLAlchemy models: `platform.py` (User, Org,
  OrgMembership, TenantMixin, sessions, PII log), `dubs.py`, `tags.py`.
- `backend/shared/` — `auth.py` (auth + `require_role`), `org_context.py`
  (resolve current org), `scoping.py` (org stamping/query helper).
- `backend/apps/dubs/`, `backend/apps/tags/` — per-app routes + services.
- `frontend/` (DG-Dubs SPA), `tags-frontend/` (DG-Tags SPA) — React + TS (CRA;
  migration to Vite planned).
- `migrations/` — Alembic migration chain.
- `tests/` — pytest suite (SQLite in-memory).

## Known follow-ups (see design doc §11a for the full list)

- Optional hardening: prod DB secrets are plaintext EB env vars (readable by
  anyone with EB/CFN read on the account). Moving them to SSM/Secrets Manager
  is a low-priority nice-to-have, not urgent for a solo project. (Command-line
  exposure during the deploy was on a private machine — not a concern.)
- In-memory `TournamentRatingSystem` (DG-Dubs read cache) is single-org; must
  be made per-org before onboarding a 2nd org.
- Migrate tenant read call-sites to org-scoped queries when multi-org lands.
- CRA → Vite before the path-based frontend deploy.
- Phase 2: fold DG-Putt into this backend (rename its tables `putt_*`).
