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
- **DG-Putt** — putting league. Live at https://putt.dg-rater.com, served by a
  *separate* project/repo (`../puttingLeague/`) and EB env **in prod**. Its
  backend has now been **folded into this repo** (`backend/apps/putt/`,
  `putt_*` tables) on `main`, but that consolidated code is **not yet deployed**
  and prod still runs from the standalone repo until cutover (design doc
  Phase 2).

## Current state (as of 2026-11-07)

- **DG-Putt backend fold-in (Phase 2): MERGED to `main`, NOT yet deployed.**
  DG-Putt's backend is consolidated into this app factory (PR #68): nine
  `putt_*` tables (`backend/models/putt.py`, org-scoped via `TenantMixin`), all
  routes under `/api/putt/*` (`backend/apps/putt/`) on the shared two-axis auth
  (`require_role(app='putt', ...)`), SocketIO added to `create_app` for live
  bracket updates, and Alembic migration `d4e5f6a7b8c9` (creates the `putt_*`
  tables; rehearsed reversible on MySQL). **The prod cutover is deliberately
  pending** — it requires, in order: (1) `flask db upgrade` on the shared RDS
  to create the `putt_*` tables, (2) a one-off `dgputt`→`putt_*` data migration
  stamped `org_id=1` (run between events — the season is live), then (3) deploy
  + repoint the Putt frontend + 301 `putt.dg-rater.com`. Until then the
  standalone `puttingLeague` repo keeps serving prod untouched.
- **Frontend CRA → Vite (Phase 2.5): all three SPAs migrated.** DG-Dubs
  (`frontend/`), DG-Tags (`tags-frontend/`), and DG-Putt (`putt-frontend/`,
  copied in from `../puttingLeague/frontend/` during the monorepo
  consolidation) are all on Vite — pure tooling swap, `base: '/'` (no routing
  change yet), `build/` output preserved so the existing `aws s3 sync build/`
  deploy is unchanged. Required bumping `@types/node`→20 and `typescript`→5.x
  (Vite 5 / bundler resolution). DG-Putt keeps `socket.io-client`; its Vite dev
  server proxies both `/api` and `/socket.io` (ws) to the backend. **DG-Putt's
  frontend API calls were repointed to `/api/putt/*`** (shared `/api/auth/*`
  left as-is), so the consolidated stack is testable locally — verified live
  (players/tournaments/ace-pot/seasons + socket.io handshake). **Known gap:**
  the DG-Putt Admin user-management tab is broken pending the §13 governance
  migration (see follow-ups). **Still CRA: none.** Remaining Phase 2.5:
  path-based routing + single distribution.
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
  `migrations/`; chain head `d4e5f6a7b8c9` = the DG-Putt `putt_*` tables; prod
  RDS is currently at `c3d4e5f6a7b8` since the putt migration is not yet
  applied). `db.create_all()` is only used for the SQLite test DB.
- The **URL direction** is path-based, org-first: `dg-rater.com/<org>/<app>`
  (e.g. `/svdgc/tags`). Not all frontends serve this yet.

## Layout

- `backend/app.py` — Flask app factory (`create_app`).
- `backend/models/` — SQLAlchemy models: `platform.py` (User, Org,
  OrgMembership, OrgRole, TenantMixin, sessions, PII log), `dubs.py`, `tags.py`,
  `putt.py` (nine `putt_*` tables).
- `backend/shared/` — `auth.py` (auth + `require_role` / `require_org_role`),
  `org_context.py` (resolve current org), `scoping.py` (org stamping/query
  helper).
- `backend/apps/dubs/`, `backend/apps/tags/`, `backend/apps/putt/` — per-app
  routes + services.
- `frontend/` (DG-Dubs), `tags-frontend/` (DG-Tags), `putt-frontend/`
  (DG-Putt, incl. `socket.io-client`) — React + TS SPAs, all **on Vite**.
  DG-Putt's SPA was copied in from `../puttingLeague/frontend/`; the standalone
  copy still serves prod until cutover.
- `migrations/` — Alembic migration chain.
- `tests/` — pytest suite (SQLite in-memory).

## NEXT SESSION — frontend consolidation (START HERE)

Phase 1 + §13 + the DG-Putt **backend** fold-in are all landed. Current effort
is **Phase 2.5 frontend consolidation** on branch `frontend-vite-migration`:

1. **DONE — DG-Dubs CRA → Vite** (`frontend/`). Live-verified against :5000.
2. **DONE — DG-Tags CRA → Vite** (`tags-frontend/`). Build-verified.
3. **DONE — DG-Putt SPA copied in** (`putt-frontend/`) + CRA → Vite.
   Build-verified (95 modules, socket.io-client intact). API calls still target
   the standalone `/api/tournaments` paths; `/api/putt/*` repoint is deferred to
   cutover.
4. **NEXT — path-based routing + single distribution** (own chunk). Decide
   first: **separate path-prefixed builds** (each app its own Vite build at
   `base=/svdgc/<app>/`, synced into one S3 bucket) **vs a single unified SPA**
   (one Vite project, client-side routing over `/<org>/<app>`, one dev server).
   Then: React Router `basename` per app, landing/directory page at `/`,
   CloudFront SPA-routing behaviors, 301 `putt.dg-rater.com` → `/svdgc/putt`.
   (Also fold in: give each dev server a distinct port so all can run at once.)

**DG-Putt prod cutover (backend) — still pending, do NOT do piecemeal:**
snapshot shared RDS → `flask db upgrade` (`d4e5f6a7b8c9`, additive, safe
anytime) → one-off `dgputt`→`putt_*` data copy stamped `org_id=1` (between
events) → deploy consolidated backend → repoint Putt frontend → retire
standalone env. `main` is kept at deployed-prod state so a season hotfix can
ship from the standalone `puttingLeague` repo without interference.

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
- CRA → Vite: **all three SPAs done** (`frontend/`, `tags-frontend/`,
  `putt-frontend/`). Remaining Phase 2.5: path-based routing + single
  distribution; DG-Putt frontend API repoint to `/api/putt/*` **done**.
- **DG-Putt Admin user-management tab broken, pending the §13 governance
  migration.** `putt-frontend/src/components/Admin.tsx` still assumes DG-Putt's
  old single-axis auth: it calls the nonexistent `/api/auth/reset-data` and
  uses `user_id` / `Admin`/`Director` role enums instead of the shared `id` +
  `org_roles`/`org_memberships` model. Rest of the DG-Putt SPA works against the
  consolidated backend. Fix = rebuild the tab on the governance model (not a
  patch). See design doc §13.8.
- Phase 2: DG-Putt backend fold-in **done on `main`** (`putt_*` tables,
  `/api/putt/*`). Remaining: prod data cutover + frontend copy-in/repoint.
