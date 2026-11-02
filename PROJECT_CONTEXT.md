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

## Current state (as of 2026-10-20)

- **Org-level governance (Phase 1) is DEPLOYED to prod.** All domain data is
  scoped to an organization via an `org_id` column on tenant tables, with a
  `before_flush` hook that stamps org ownership on writes.
- **Org-Role Tier (design doc §13): FULLY DEPLOYED. ✅ (completed 2026-10-20)**
  The §13 migration (`c3d4e5f6a7b8`) was applied to prod RDS on 2026-10-09, and
  the matching `main` code was deployed to the EB `production` env on
  2026-10-20 — **from the travel laptop** (ran `eb init`/`eb use production`
  here; `.elasticbeanstalk/` is gitignored but the EB env lives in AWS, so
  deploying from a second machine is fine and does not affect the desktop).
  The auth-handover window is closed: public reads and admin/director
  authenticated actions both verified working post-deploy.
  - Deploy gotcha (for next time): with stray installer artifacts in the repo
    root (`kirocli.zip` ~552MB, `awscliv2.zip` ~73MB), `eb deploy` zipped the
    working dir and hit the 512MB archive limit. Fix was to keep those files
    out of the project dir and ensure `.ebignore` excludes them (note:
    `.ebignore`, when present, REPLACES `.gitignore` for EB bundling).
- Authorization is now **two-axis**:
  - a per-app operational tier — `org_memberships` (roles: `admin` /
    `director`; one row per `(user, app)`, no wildcard);
  - an org-wide governance tier — `org_roles` (roles: `owner` / `manager`),
    which derives app-admin on every subscribed app;
  - plus a `users.is_superuser` platform bypass (cross-org).
  "Viewer" is **not** a stored role — it means *no membership* (public read).
- The single existing org is **Silicon Valley Disc Golf Club (SVDGC,
  `org_id=1`)**; all pre-existing data was backfilled to it.
- Schema is managed by **Alembic / Flask-Migrate** (migrations under
  `migrations/`; prod head `c3d4e5f6a7b8`). `db.create_all()` is only used for
  the SQLite test DB.
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

## NEXT SESSION — post-§13 cleanup (START HERE)

The §13 deploy is DONE (see Current state). Remaining follow-ups:

1. ~~Set `users.is_superuser` on the site-owner account.~~ **DONE 2026-10-20.**
   Set `admin` (user id 1) to `is_superuser=True` on prod RDS. Method: connected
   to the EB instance (`i-0d7e6cb8dc9147dc5`) via **SSM Session Manager** (not
   SSH), `sudo su -`, sourced the EB env (`set -a; . /opt/elasticbeanstalk/deployment/env; set +a`
   — needed because the root shell lacks the injected `DB_*` vars, else it
   falls back to localhost), activated `/var/app/venv/staging-LQM1lest`, and ran
   a one-off ORM script scoped to `username='admin'`. Verified before/after.
   Reversible: set back to `False` to undo. (Still a manual DB flag until an
   admin portal exposes user management, §13.8.)
2. **Delete the pre-migration snapshot** `dgputt-db-pre-s13-20260109` after a
   few clean days.
3. ~~Revoke temporary SG rule~~ — N/A; no SG rule was created this session
   (deployed via EB, not a direct DB connection).
4. ~~Rotate prod DB password~~ — deprioritized; exposure was on a personal,
   non-shared laptop. (Original note still stands long-term: `DB_PASSWORD` and
   `ADMIN_PASSWORD` share one value and should differ.)
5. **Commit the `.ebignore` fix** (excludes `kirocli*`, `awscliv2.zip`,
   `*.zip`, `backend/venv/`, `tags-frontend/`, etc.) so future deploys from any
   machine don't hit the 512MB archive limit.

Rollback if the deploy misbehaves: redeploy the prior app version, or
`flask db downgrade b2f1c3a4d5e6` (proven reversible — re-materializes the four
`'*'` rows), or restore snapshot `dgputt-db-pre-s13-20260109` (nuclear; also
rolls back the DG-Putt `dgputt` schema on the shared instance).

## Known follow-ups (see design doc §11a and §13 for the full list)

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
