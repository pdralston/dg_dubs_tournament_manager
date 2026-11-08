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

- **Unified single-SPA frontend (`web/`): IN PROGRESS (all 3 apps ported; wiring/cleanup next).**
  Decision taken to go straight to the **single unified SPA** (design doc §4
  north star) instead of the interim path-prefixed separate builds — one Vite
  app, one build, one bucket/CloudFront, client-side routing over
  `/:org/:app/*`. Built on a long-lived `single-spa-implementation` integration
  branch (interim CRs merge into it; one final CR to `main` when whole). The
  `spa/01` scaffold added `web/`: router (`/` platform landing, `/:org` org
  landing, `/:org/:app/*` app host), app shell (brand + org/app switcher + auth
  slot + shared login modal), and a shared three-tier `AuthContext` (Site
  `isSuperuser` → Org `orgRole` owner/manager → App `appRole` admin/director,
  mirroring the backend) wired to the enriched `/api/auth/me`. **All three apps
  are ported and live-verified** into `web/src/apps/{dubs,tags,putt}/` (`spa/03`
  Dubs, `spa/04` Tags, `spa/05` Putt incl. Socket.IO live bracket updates).
  A build-time PostCSS plugin (`web/postcss-scope-app.mjs`) scopes each app's
  CSS under its `[data-app]` host so the three apps' reused class names + `:root`
  vars don't collide in the one DOM.
  The standalone `frontend/`, `tags-frontend/`, `putt-frontend/` are superseded
  and get removed once all apps are ported into `web/src/apps/` (`spa/06`).
- **`/api/auth/me` enriched (on `main`, PR #71).** Returns the three-tier
  identity (`is_superuser`, `org_role`, `app_roles`) alongside the legacy flat
  fields, so the SPA auth context can gate UI the same way the backend gates the
  API (same resolvers).
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
  copy still serves prod until cutover. **Being superseded by `web/`** — the
  unified single SPA (shell + router + shared AuthContext; apps port into
  `web/src/apps/{dubs,tags,putt}/`). The three `*-frontend/` dirs get removed
  once their ports land.
- `web/` — unified single-SPA (Vite): `src/{auth,shell,host,router,landing,apps}`.
- `migrations/` — Alembic migration chain.
- `tests/` — pytest suite (SQLite in-memory).

## NEXT SESSION — frontend consolidation (START HERE)

Phase 1 + §13 + the DG-Putt **backend** fold-in are all landed, and all three
SPAs are on Vite. Current effort is the **unified single SPA** (`web/`) on the
long-lived `single-spa-implementation` integration branch (interim CRs merge
into it; one final CR to `main`). Decision: single unified SPA (not interim
path-prefixed separate builds).

1. **DONE — `spa/01` shell scaffold.** `web/` Vite app: router (`/`, `/:org`,
   `/:org/:app/*`), app shell (org/app switcher + auth slot), shared three-tier
   `AuthContext` wired to enriched `/api/auth/me`, placeholder landings + app
   mounts. Build-verified; live nav verified.
2. **DONE — shared `AuthContext` validated live** (folded into `spa/03`): login
   via the shell's `LoginModal` → `/api/auth/me` tiers → per-app gating, all
   confirmed working. (No separate `spa/02` branch was needed.)
3. **DONE — `spa/03` port DG-Dubs** into `web/src/apps/dubs/`. Components copied
   verbatim (take a `userRole` string → fed `appRole('dubs')`); `DubsApp`
   consumes `useAuth()`; shared `LoginModal` added to the shell. Live-verified.
4. **DONE — `spa/04` port DG-Tags** into `web/src/apps/tags/`. Data components
   don't touch auth (gating was only in the old App.tsx) → no adapter context
   needed; `TagsApp` uses shared `useAuth()` (`hasAppRole('tags',…)`). Tags API
   = `/api/tags/*` + shared `/api/auth/*` (unchanged). Live-verified.
5. **DONE — `spa/05` port DG-Putt** into `web/src/apps/putt/` (Socket.IO live
   bracket updates working; API already `/api/putt/*`; role-casing bridge
   lowercase→`Admin`/`Director`; Admin user-mgmt tab still the §13.8 gap).
   Live-verified against prod (styling/fonts match). Local test data: `DRoc101`
   granted `(putt,director)`; `admin` has putt via superuser.
   **spa/05 also carries the per-app CSS-scoping plugin + the post-merge layout
   fixes** (see the CSS-isolation bullet below): full-width shell
   (`.dgr-content` padding→0), Putt back-button (static position + copied
   `back-arrow-circle.png`/`dg-basket-grn.svg` into `web/public/` + light text
   on green), matches-in-progress bar made static, `.sr-only` utility added to
   shell `index.css`, players table `table-layout: auto` fit. All build- +
   live-verified. Known deferred visual passes (NOT yet exercised live): Putt
   tournament create/manage, bracket view mid-tournament, Admin tab; and a
   Dubs/Tags full-width re-check — handle as follow-ups, not blockers.

6. **START HERE NEXT SESSION — `spa/06`** (after `spa/05` merges). Two parts:
   (a) **Code/cleanup in-repo:** delete the superseded `frontend/`,
   `tags-frontend/`, `putt-frontend/` dirs; update README/docs to point at
   `web/` as the sole frontend; decide dev-server ports (each app no longer has
   its own server — `web/` is one dev server, so this is moot now). Commit as an
   `spa/06` CR into `single-spa-implementation`.
   (b) **AWS deploy wiring (needs operator + live-resource confirmation; do NOT
   execute blind):** build `web/` → one S3 bucket (reuse `dg-rater-com`) behind
   one CloudFront distro; add SPA-fallback (serve `web/`'s `index.html` for any
   non-`/api`, non-`/socket.io` path); 301 `putt.dg-rater.com` →
   `dg-rater.com/svdgc/putt`; retire the old per-app distributions after soak.
   Then the **final CR `single-spa-implementation` → `main`**.

**Port-pattern lessons (apply to Putt):**
- **Keep each app's own header/banner; strip ONLY its auth controls** (login/
  logout/user) — the shell owns those. If the app header was `position: fixed`,
  override to `static` so it flows under the shell's org bar, and drop any
  `main` top-offset that compensated for the fixed header.
- **Add an appRole-loss reset guard:** when `appRole(app)` drops (e.g. logout),
  reset any privileged view to a public one AND hard-guard the privileged
  render — otherwise privileged content lingers after logout (a real leak found
  in Dubs).
- Feed `appRole(app) ?? 'Viewer'` as the legacy `userRole` string prop; shape
  `identity` into the app's `User`/`currentUser` for admin components.
- **Per-app CSS isolation is handled by a build-time PostCSS plugin**
  (`web/postcss-scope-app.mjs`, wired in `web/vite.config.ts`): it auto-scopes
  every rule in `src/apps/<app>/*.css` under `[data-app="<app>"]`
  (`:root`/`html`/`body` → the host; `@media` children scoped; `@import`/
  `@keyframes`/`@font-face` left global; idempotent vs already-scoped
  selectors). This is required because the three apps reuse class names (`.App`,
  `.App-header`, `.table-container`, …) and `:root` var names (`--accent`,
  `--color-page-bg`, …) with different values. Three latent couplings it
  surfaced (all fixed): (a) apps' palettes collided via global `:root` — the
  plugin scopes them; (b) Putt never imported its own `styles/theme.css` (it had
  been borrowing Dubs' leaked global vars) — add the theme import per app;
  (c) each app must **anchor its base typography on its host** (a `body { font-
  family: var(--font-*) }` rule, which the plugin rewrites to the host), not
  rely on a global `body` font — the standalone apps' `index.css` body fonts are
  NOT ported (the shell owns `body`). (esbuild minifies `[data-app="x"]`→
  `[data-app=x]` in the bundle.)

**Seed-data / auth note (address before prod cutover):** the §13 migration made
every director a director of BOTH `dubs` and `tags` (directors-of-everything).
Per-app scoping works correctly (verified: a dubs-only director gets
`tags: null`); the memberships just need curating to intended real-world scope
before go-live. Separately, **DG-Putt user reconciliation** at cutover: DG-Putt's
`users` table (`admin`, `DRoc101`, `Mr. Hilbert`, `Hal Kurz`; scrypt hashes) is
NOT folded in as a table — unify on shared `users` + memberships. `admin` and
`DRoc101` are the operator's existing shared accounts (dedupe by username: admin
already has putt via superuser; grant `DRoc101` `(putt,director)`). `Mr. Hilbert`
/`Hal Kurz` need shared accounts created with FRESH passwords (scrypt≠shared
PBKDF2, can't port) + `(putt,director)` — or dropped if stale. DG-Putt `users`
rows discarded. (See design doc §7/§8.)

**DG-Putt prod cutover (backend) — still pending, do NOT do piecemeal:**
snapshot shared RDS → `flask db upgrade` (`d4e5f6a7b8c9`, additive, safe
anytime) → one-off `dgputt`→`putt_*` data copy stamped `org_id=1` (between
events) → deploy consolidated backend → repoint Putt frontend → retire
standalone env. `main` is kept at deployed-prod state so a season hotfix can
ship from the standalone `puttingLeague` repo without interference.

## Remaining big-picture workplan (ordered)

1. **`spa/06`** — frontend finalize: delete old `*-frontend/` dirs + AWS deploy
   wiring (single bucket/CloudFront + SPA fallback + 301), then CR
   `single-spa-implementation` → `main`. (See step 6 above.)
2. **DG-Putt backend prod cutover** — the RDS `flask db upgrade` + `dgputt`→
   `putt_*` data migration + consolidated-backend deploy (see cutover block
   above). Gate behind an RDS snapshot; run the data copy between putt events.
3. **Pre-go-live data curation (decide with operator):**
   - Curate `org_memberships` to intended per-app scope (the §13 migration made
     every director a director of both dubs+tags — "directors of everything").
   - **DG-Putt user reconciliation:** `admin`/`DRoc101` dedupe to existing
     shared accounts (admin has putt via superuser; grant `DRoc101` putt); decide
     migrate-or-drop for `Mr. Hilbert` / `Hal Kurz` (fresh passwords — scrypt
     can't port). **OPEN QUESTION pending operator.**
   - Optionally set `users.is_superuser` properly (currently owner-equiv only).
4. **Deferred governance-frontend work (§13.8):** rebuild the DG-Putt (and the
   DG-Dubs) Admin user-management tabs on the two-axis model; `/api/org/*`
   endpoints; `org_app_subscriptions` entitlements. Putt Admin tab is currently
   non-functional against the shared auth (documented in Admin.tsx banner).
5. **Deferred visual QA passes** (non-blocking): Putt tournament create/manage,
   bracket mid-tournament + live Socket.IO update, Admin tab; Dubs/Tags
   full-width re-check.

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
