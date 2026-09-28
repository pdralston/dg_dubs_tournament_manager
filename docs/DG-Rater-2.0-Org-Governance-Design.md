# DG-Rater 2.0 — Org Governance & App Consolidation Design

Status: Draft
Author: (pdralsto)
Last updated: 2026-09-27

## 1. Summary

DG-Rater today is three disc-golf apps split across two Elastic Beanstalk
environments and two frontends per app, all sharing a single RDS MySQL
instance. This document proposes consolidating the three backends
(DG-Dubs, DG-Tags, DG-Putt) into the single Flask app-factory that already
serves DG-Dubs + DG-Tags, and introducing an **organization-level governance
layer** so that all domain data is scoped to an org and users are authorized
per-org and per-app.

The multi-tenancy approach is **Option A: shared schema with an `org_id`
column on every tenant-owned table**, enforced by a query-scoping layer. This
is the lowest-cost, lowest-ops option and fits a solo-primary passion project
with a small number of trusted co-admins. True multi-org onboarding (public
directory, self-service org creation) is explicitly a **future scaling phase**,
not part of the initial rollout — but the schema and authZ model are designed
now so that later scaling does not require a second migration.

## 2. Goals / Non-Goals

### Goals
- One EB environment / one Flask process serving DG-Dubs, DG-Tags, DG-Putt.
- An `Organization` entity; all domain data scoped to an org.
- AuthZ model expressing `(user, org, app, role)` so a user can hold different
  roles in different orgs/apps.
- No data loss; existing dg-rater.com (Dubs/Tags) and putt.dg-rater.com data
  preserved and back-filled to a default org.
- Reduce recurring cost by collapsing two EB environments into one.

### Non-Goals (this phase)
- Public self-service org signup / org directory UI.
- Payment/billing per org.
- Cross-region or multi-AZ HA.
- Schema-per-org or database-per-org isolation (see Alternatives).
- Card creation (DG-Tags P0.5) and payouts (P1) — unchanged by this work.

## 3. Current State (confirmed)

### 3.1 Code
- **This repo (`dg_dubs_tournament_manager`)** is already refactored to a Flask
  app-factory (`backend/app.py: create_app`) that registers DG-Dubs blueprints
  (`backend/apps/dubs/routes/`) and the DG-Tags blueprint
  (`backend/apps/tags/`), with a unified model registry (`backend/models/`:
  `platform.py`, `dubs.py`, `tags.py`) and shared session auth
  (`backend/shared/auth.py`). DG-Tags is fully implemented and tested
  (`tests/test_tags_lifecycle.py`).
  - Note: legacy pre-refactor code still exists and is dead:
    `backend/api/`, `backend/auth.py`, top-level `tournament_core/`,
    `tournament_manager.py`. Recommend deleting during this work.
- **DG-Putt (`../puttingLeague/`)** is a **separate** Flask app
  (`backend/app.py`, `backend/models.py`, `backend/routes/*`) with its own
  auth (`routes/auth.py`) and its own EB deploy. It is NOT yet on the
  app-factory/blueprint structure.
- Auth today is a flat `User(role in {admin, director, viewer})` model with
  DB-backed sessions (`UserSession`), PBKDF2 password hashing. There is **no
  org concept** in either codebase.

### 3.2 Infrastructure (AWS account 839087536917, us-west-2)
Confirmed via live inspection:

| Component | Detail |
|-----------|--------|
| EB env `D-Rater/production` | e-9qqydjxwxi, SingleInstance, t3.micro, Python 3.13 AL2023, Green. Serves DG-Dubs + DG-Tags API. `DB_NAME=dg_dubs`. |
| EB env `DG-Putt/dgputt-api` | e-wgcvyfa6pp, Python 3.13 AL2023, Green. Serves DG-Putt API. `DB_NAME=dgputt`. |
| RDS `dgputt-db` | MySQL 8.4, db.t3.micro, single-AZ, gp2 20GB, storage-encrypted, deletion-protection ON, publicly accessible. **Single shared instance.** |
| CloudFront `dg-rater.com` | → S3 `dg-rater-com` (Dubs SPA) |
| CloudFront `api.dg-rater.com` | → EB `production` origin |
| CloudFront `putt.dg-rater.com` | → S3 `putt-dg-rater-com` (Putt SPA) |
| CloudFront `api.putt.dg-rater.com` | → EB `dgputt-api` origin |
| (none) `tags.dg-rater.com` | not yet provisioned; Tags SPA still in dev |

Key facts:
- **Data separation is schema-per-app on one instance**: Dubs/Tags use schema
  `dg_dubs`; Putt uses schema `dgputt`. (Tags tables live inside `dg_dubs`.)
- Both API origins are `http-only` custom origins behind CloudFront with
  full method sets and appropriate cache/origin-request policies.
- Secrets (`DB_PASSWORD`, `SECRET_KEY`, `ADMIN_PASSWORD`) are stored as
  **plaintext EB environment variables**. See §9 Security Hardening.

## 4. Target Architecture

**URL architecture decision (committed): path-based, org-first.**
`dg-rater.com/<org>/<app>` for the UI; `api.dg-rater.com/api/<app>/*` for the
API (org resolved from session/URL context). Chosen over subdomain-per-app
(`<app>.dg-rater.com`) because it (a) matches the org-first tenancy model,
(b) collapses all frontends to a single S3 bucket + CloudFront distribution
(no per-app/per-org infra), and (c) makes a shared login trivial — one origin,
one cookie, one CORS entry. See §10 for the rejected subdomain alternative.

```
                    dg-rater.com  (single CloudFront + S3 origin)
                              │
        ┌─────────────────────┼─────────────────────────┐
        │  /                  │  /<org>/dubs             │  public org
        │  landing + org      │  /<org>/tags             │  directory
        │  directory + login  │  /<org>/putt             │
        └─────────────────────┴──────────┬──────────────┘
                                          │ XHR → api.dg-rater.com/api/<app>/*
                        ┌─────────────────▼────────────┐
                        │  Single Flask app (1 EB env)  │
                        │  create_app():                │
                        │   /api/dubs/*  (blueprint)    │
                        │   /api/tags/*  (blueprint)    │
                        │   /api/putt/*  (blueprint)    │
                        │   /api/org/*   (governance)   │
                        │   /api/auth/*  (shared)       │
                        │  org-scoping middleware       │
                        │  (current_org from URL/session)│
                        └───────────────┬───────────────┘
                                        ▼
                        ┌──────────────────────────────┐
                        │  RDS MySQL (dgputt-db)         │
                        │  single schema, org_id on      │
                        │  every tenant-owned table      │
                        └──────────────────────────────┘
```

- One EB environment (reuse `D-Rater/production`) hosts the consolidated
  Flask process. `DG-Putt/dgputt-api` is retired after cutover.
- One API hostname (`api.dg-rater.com`) fronts all three apps under
  `/api/<app>/*` path prefixes.
- **One frontend distribution.** `dg-rater.com` serves a landing/directory
  page plus the app SPAs under path prefixes. Near-term the three CRA builds
  are deployed into one S3 bucket under `/<org>/dubs`, `/<org>/tags`,
  `/<org>/putt` path prefixes (each CRA built with the matching
  `homepage`/`PUBLIC_URL` and router `basename`); the long-term end state is a
  single SPA with client-side routing over `/<org>/<app>`.
- **No `tags.dg-rater.com` (or any new per-app) subdomain is provisioned.**
  This removes the infra blocker that stalled the DG-Tags deploy.
- `putt.dg-rater.com` stays live during transition, then 301-redirects to
  `dg-rater.com/svdgc/putt`.

## 5. Tenancy Data Model (Option A: shared schema + `org_id`)

### 5.1 New governance tables

```
organizations
  org_id            INT PK AUTO_INCREMENT
  slug              VARCHAR(64) UNIQUE   -- e.g. "svdgc"; used in URLs/directory
  name              VARCHAR(200)
  is_active         BOOL DEFAULT TRUE
  created_at        DATETIME

org_memberships           -- a user's role within an org, optionally per app
  membership_id     INT PK AUTO_INCREMENT
  org_id            INT FK -> organizations(org_id)
  user_id           INT FK -> users(id)
  app               ENUM('dubs','tags','putt','*')  -- '*' = all apps in org
  role              ENUM('admin','director','viewer')
  created_at        DATETIME
  UNIQUE(org_id, user_id, app)
```

`users` stays global (identity is cross-org). Authorization is expressed only
through `org_memberships`. A platform "super admin" is modeled as a row with
a reserved org or a `users.is_superuser` flag (see §6).

### 5.2 `org_id` on tenant-owned tables

Every domain table gets a non-null `org_id INT FK -> organizations(org_id)`,
indexed. Tables in scope:

- DG-Dubs: `players`, `tournaments`, `teams`, `player_history`,
  `tournament_participants`, `ace_pot_tracker`, `ace_pot_config`, `seasons`.
- DG-Tags: `tag_members`, `member_contact_info` (via member),
  `tag_events`, `tag_registrations`, `tag_history`, `tag_inventory`,
  `tag_unavailable`.
- DG-Putt: its player/tournament/match/archive tables (in `dgputt` schema
  today — merged into the unified schema during migration).

Global/non-tenant tables (no `org_id`): `users`, `user_sessions`,
`organizations`, `org_memberships`. `pii_access_log` keeps `org_id` for
audit filtering.

### 5.3 Uniqueness scoping

Any existing "unique per system" constraint that is really "unique per org"
must be re-scoped to include `org_id`. Examples:
- `tag_inventory.season_year` UNIQUE → `UNIQUE(org_id, season_year)`.
- `tag_unavailable UNIQUE(season_year, tag_number)` →
  `UNIQUE(org_id, season_year, tag_number)`.
- `tag_registrations UNIQUE(event_id, member_id)` stays valid (event already
  belongs to an org) but member/event must belong to the same org — enforced
  in the service layer.
- DG-Dubs player name uniqueness (if any) → per-org.

### 5.4 Query scoping enforcement

To avoid every query manually adding `.filter_by(org_id=...)` (error-prone and
the main risk in Option A), introduce a scoping layer:

- A request-scoped `current_org_id` resolved once per request (from the
  authenticated membership + selected org; see §6.3).
- A SQLAlchemy pattern for tenant models: a common `TenantModel` mixin plus a
  helper `tenant_query(Model)` that always injects
  `Model.org_id == g.current_org_id`. Service code calls `tenant_query(...)`
  instead of `Model.query`.
- Writes: a `before_flush` / session event that stamps `org_id` on new tenant
  rows from `g.current_org_id` and rejects cross-org writes.
- Defense in depth: DB-level `org_id` NOT NULL + FK, and code review rule that
  raw `Model.query` on tenant models is disallowed (lint/grep check in CI).

This keeps the isolation guarantee in one place rather than scattered across
~40 endpoints.

## 6. AuthZ Model `(user, org, app, role)`

### 6.1 Roles (unchanged semantics, now org/app-scoped)
- **admin** — full CRUD within the org/app, incl. PII and inventory.
- **director** — event/data operations, PII write-blind (Tags), no inventory
  admin.
- **viewer** — public read (unauthenticated users are implicit viewers).

### 6.2 Resolution
On login, the user may belong to multiple orgs. The session establishes:
`user_id`, and the set of `(org_id, app, role)` memberships. The active org is
selected explicitly (single-org users auto-select). The active org is stored
in the session and echoed to the client.

### 6.3 Decorators (evolve `backend/shared/auth.py`)
Replace the flat `login_required` / `admin_required` with org/app-aware
checks. Proposed:

```
@require_role(app='tags', role='director')   # within current_org
@require_role(app='tags', role='admin')
```

`require_role`:
1. Validates the session token against `user_sessions` (as today).
2. Resolves `g.current_org_id` from session-selected org.
3. Looks up the membership `(current_org_id, user_id, app in {requested,'*'})`.
4. Compares role rank (admin > director > viewer).
5. 401 if unauthenticated, 403 if authenticated but insufficient/no membership.

PII gating (currently reading `session['role']` directly in
`get_members`) must route through this DB-validated resolution instead of the
raw session cookie — closes the hardening gap noted in earlier review.

### 6.4 Super admin
For platform operations (create orgs, cross-org support), add
`users.is_superuser BOOL`. Superuser bypasses membership checks. Only the
primary operator holds it. This avoids needing a synthetic "root org".

## 7. App Consolidation (fold DG-Putt into the app factory)

DG-Putt is the largest lift because it is a separate stack.

1. **Move code** into `backend/apps/putt/` as `routes.py`/`routes/` +
   `services.py`, mirroring the Tags/Dubs layout.
2. **Merge models** from `../puttingLeague/backend/models.py` into
   `backend/models/putt.py`, re-exported from `backend/models/__init__.py`.
   **Confirmed collision (must resolve):** DG-Putt and DG-Dubs define tables
   with the *same names but different columns*:
   - `users` — Putt: PK `user_id`, `role Enum('Admin','Director','Viewer')`,
     werkzeug password hashes. This repo: PK `id`, lowercase string `role`,
     PBKDF2 hashes + `salt`, plus `user_sessions`. Two different auth models
     sharing one table name.
   - `seasons` — same name, near-identical shape (reconcilable).
   - `tournaments` — Putt has bracket/match fields (`stations`, `payout_config`,
     `first/second_payout`); Dubs is doubles-rating oriented. Incompatible.
   - `teams` — Putt: `seed_number`, `final_place`, `points_earned`; Dubs:
     `expected_position`, `team_rating`, `payout`. Incompatible.
   - Putt-only tables: `registered_players`, `tournament_registrations`,
     `team_history`, `season_standings`, `ace_pot`, `matches`.
   **Resolution:** Putt domain tables MUST be renamed to `putt_*`
   (e.g. `putt_tournaments`, `putt_teams`, `putt_players`, `putt_matches`,
   `putt_seasons`). Do NOT share `tournaments`/`teams`/`seasons` across apps —
   they are genuinely different domains (this is exactly why the two apps sit
   in separate MySQL schemas today). Putt's `users` is folded into the shared
   `users` + `org_memberships` model, not kept as a table.
3. **Unify auth**: delete DG-Putt's `routes/auth.py`; it uses the shared
   `/api/auth/*` and `backend/shared/auth.py`. Migrate any Putt-specific
   fields into the shared `users`/membership model.
4. **Register blueprint** with `url_prefix='/api/putt'` in `create_app()`.
5. **Frontend**: point `../puttingLeague/frontend` `REACT_APP_API_URL` at
   `https://api.dg-rater.com` and its calls at `/api/putt/*`.
6. **CORS**: add putt.dg-rater.com origin to the CORS allow-list in
   `create_app()` (already lists dg-rater.com, tags.dg-rater.com).

## 8. Migration & Rollout Plan

Ordered, each step independently reversible where possible. **Take a fresh
RDS snapshot before any schema change.**

### Phase 0 — Prep (no prod impact)
- Delete dead legacy code in this repo (§3.1).
- Add governance tables + `org_id` columns behind code that tolerates a single
  implicit org (default `org_id = 1`, slug `dg-rater`).
- Write Alembic-style migrations (introduce Alembic; today schema is created
  via `db.create_all()` which cannot alter existing tables).

### Phase 1 — Governance schema (Dubs/Tags schema `dg_dubs`)
- Create `organizations`, seed the default org:
  `org_id=1, slug='svdgc', name='Silicon Valley Disc Golf Club'`. All existing
  data in `dg_dubs` (and, in Phase 2, `dgputt`) belongs to SVDGC.
- Create `org_memberships`; back-fill: every existing `users` row gets a
  membership `(org 1/svdgc, user, app='*', role=<existing role>)`.
- Add `org_id` (nullable), back-fill all existing Dubs/Tags rows to org 1,
  then set NOT NULL + FK + indexes. Re-scope unique constraints (§5.3).
- Deploy consolidated app to `production` with scoping layer active. Verify
  Dubs + Tags behavior unchanged (single org, URLs under `/svdgc/...`).

### Phase 2 — Fold in DG-Putt
- Migrate `dgputt` schema data into the unified schema (`dg_dubs`) under
  distinct Putt table names, stamping `org_id = 1`.
  - Approach: `mysqldump` the `dgputt` schema, transform table names, load into
    `dg_dubs`; or write a one-off Python migration reading both schemas.
- Back-fill Putt users into shared `users` + memberships (dedupe by username;
  the primary operator is likely the same identity across apps).
- Deploy the app factory now including the Putt blueprint.
- Repoint the Putt SPA to call `api.dg-rater.com/api/putt/*`. Keep the old EB
  running as fallback during soak.
- Soak. Then retire `DG-Putt/dgputt-api` EB env and (optionally) the
  `dgputt` schema after a retention window.

### Phase 2.5 — Frontend consolidation to single distribution
- **Prerequisite — migrate frontends CRA → Vite.** Create React App was
  deprecated by the React team (Feb 2025) and `react-scripts` is effectively
  unmaintained. All three SPAs (`frontend/`, `tags-frontend/`, DG-Putt's) are
  CRA-based. Migrate each to Vite *before* wiring path-based serving, because
  Vite's `base` option configures the sub-path (`/svdgc/<app>/`) far more
  cleanly than CRA's `homepage`, so doing CRA path-prefixing first would be
  throwaway work. Migration is mechanical: new `index.html` entry, rename
  `REACT_APP_*` env vars to `VITE_*`, swap `react-scripts` for `vite` +
  `@vitejs/plugin-react`, set `base` per app. This is an independent workstream
  from the governance backend and does not block Phase 1.
- Provision (if not already) the single frontend: reuse S3 `dg-rater-com` +
  CloudFront `E1X7Y3M3J92BY0` (the existing dg-rater.com distribution).
- Build each app with its path prefix via Vite `base`: Dubs
  `base=/svdgc/dubs/` (or root during interim), Tags `base=/svdgc/tags/`, Putt
  `base=/svdgc/putt/`, each with the React Router `basename` set to match. Sync
  builds into the bucket under those prefixes.
- Add a landing/directory page at `/` and CloudFront SPA-routing behaviors so
  each `/<org>/<app>/*` path falls back to that app's `index.html`.
- 301-redirect `putt.dg-rater.com` → `dg-rater.com/svdgc/putt` (CloudFront
  function or S3 redirect), then retire the `putt.dg-rater.com` and
  `api.putt.dg-rater.com` distributions after a retention window.

### Phase 3 — Cost cleanup
- Confirm one EB env (`production`) serves all traffic; terminate the second
  env. Verify billing drop.

### Rollback
- Each phase gated behind a snapshot. Phase 1/2 are additive to the DB
  (nullable→backfill→NOT NULL), so rollback = redeploy prior app version;
  columns remain but are ignored. Full rollback = restore snapshot.
- Note: `production` currently has `RESTORE_FROM_BACKUP=true` — confirm what
  this triggers on deploy before cutover so a deploy doesn't unexpectedly
  restore.

## 9. Security Hardening (recommend during this work)

1. **Secrets in EB plaintext env vars (medium priority, not a public exposure).**
   `DB_PASSWORD`, `SECRET_KEY`, `ADMIN_PASSWORD` are stored as plaintext EB
   environment variables. They are NOT reachable by the public or by API
   callers. The realistic attack vectors are: (a) compromise/leak of any AWS
   credential with `elasticbeanstalk:DescribeConfigurationSettings` or
   `cloudformation:DescribeStacks` — notably the `eb-deployer` access key,
   which today unlocks all three secrets; (b) instance compromise (RCE/SSRF
   reading `os.environ`/`/proc/self/environ`), made easier by SSH open to
   `0.0.0.0/0`; (c) any over-broad IAM principal in the account.
   Moving to AWS Secrets Manager / SSM SecureString adds KMS-encryption-at-rest,
   per-secret IAM + CloudTrail auditing, and rotation — so a leaked EB-read
   credential no longer yields the secret. Recommended during consolidation,
   not an emergency. Highest-value cheap step: protect/rotate the `eb-deployer`
   access key. Also note `DB_PASSWORD` and `ADMIN_PASSWORD` are currently the
   same value; they should differ. Rotating SECRET_KEY invalidates existing
   sessions (acceptable).
2. **RDS not publicly accessible.** `dgputt-db` is `PubliclyAccessible=true`.
   Restrict to the EB security group / VPC; use a bastion or SSM for admin
   access.
3. **PII read path** must go through DB-validated membership (§6.3), not the
   raw session cookie role.
4. **Least-privilege deploy user.** `eb-deployer` should not need broad read
   of secrets; scope its IAM policy.
5. Keep `MinimumProtocolVersion TLSv1.2_2021` on all distributions (already
   set). Consider attaching a WAF ACL (currently none) once multi-org/public.

## 10. Alternatives Considered

- **Option B — schema-per-org (one instance).** Stronger isolation; per-org
  `mysqldump`/restore is trivial. Cost: connection/routing complexity, N
  schemas to migrate on every change. Overkill for a solo-primary project.
- **Option C — database-per-org (separate RDS).** Strongest isolation and
  blast-radius control. Cost: per-org RDS spend and ops — contradicts the
  cost-reduction goal. Revisit only if a paying multi-org tier emerges.
- **Keep separate EB envs.** Rejected: the primary cost driver is the second
  always-on instance, and cross-app governance is far simpler in one process.
- **URL pattern — subdomain-per-app (`<app>.dg-rater.com`, optionally
  `<org>.<app>...`).** Rejected in favor of path-based `/<org>/<app>` (§4).
  Subdomains require per-app (and, with orgs, wildcard-cert) infra, put the
  *app* above the *org* in the hierarchy (backwards from the tenancy model),
  and complicate shared login (per-origin cookies + growing per-subdomain CORS
  list). Path-based needs one distribution, one cookie, one CORS entry.

## 11. Open Questions / Decisions Needed

Resolved:
- **URL architecture:** path-based, org-first `dg-rater.com/<org>/<app>`,
  starting with the `<org>` segment from day one (default org `svdgc`). (§4)
- **Default org / data ownership:** all existing `dg_dubs` and `dgputt` data
  belongs to Silicon Valley Disc Golf Club (`org_id=1, slug='svdgc'`). (§8)
- **Putt table naming on merge:** rename to `putt_*`; do not share
  `tournaments`/`teams`/`seasons` across apps. (§7)
- **Migrations tooling:** Alembic (Flask-Migrate) adopted. `db.create_all()` is
  now gated to SQLite/tests only; migrations are authoritative for MySQL.
- **Branch strategy:** DG-Tags merged to `main`; Phase 1 governance built on
  `org-governance-phase1` branched off `main`.
- **Read-scoping strategy:** writes are org-stamped now via a `before_flush`
  hook (correct ownership from day one); read call sites keep plain `.query`
  for Phase 1 (correct because single-org) and migrate to `tenant_query` /
  a global filter when org #2 arrives. See Follow-ups.

Open:
1. Confirm the behavior of `RESTORE_FROM_BACKUP=true` on `production` before
   any redeploy.
2. Timing/window for DB password + SECRET_KEY rotation (forces re-login).
3. Production migration must also `DROP COLUMN phone` on `member_contact_info`
   (leftover from before the phone-field removal) — include in the prod cutover.

## 11a. Phase 1 Status (implemented on `org-governance-phase1`)

Done and validated locally (50/50 Tags tests pass; migration chain applied to a
faithful reproduction of prod's starting state via `scripts/prod_rehearsal.sh`):
- Governance models: `Organization`, `OrgMembership`, `User.is_superuser`.
- **Prod-ready Alembic chain (3 migrations, in order):**
  1. `185e089a4a4b` — create `organizations` + `org_memberships`, add
     `users.is_superuser`, seed SVDGC org (org_id=1).
  2. `a1b2c3d4e5f6` — create all 7 DG-Tags tables **org-scoped from the start**
     (org_id + composite uniques baked in). Prod has no tag tables yet, so this
     creates them fresh.
  3. `b2f1c3a4d5e6` — add `org_id` to the 8 **DG-Dubs** tables (which hold prod
     data), backfill to SVDGC, backfill one membership per user, re-scope
     `players.name` → `(org_id, name)`. All additive/data-safe.
- `TenantMixin` on all tenant models; org context resolution
  (`backend/shared/org_context.py`); scoping layer with `before_flush`
  stamping + cross-org write block (`backend/shared/scoping.py`).
- Org/app-aware `require_role` + `resolve_membership_role`; back-compat
  `login_required`/`admin_required` routed through membership; Tags PII gating
  moved off the raw session cookie to DB-validated membership.

### Production migration runbook (when deploying Phase 1)
Prod `dg_dubs` today = only the 10 DG-Dubs + auth tables (verified 2026-09-27);
no tag tables, no governance tables, no `org_id`, no `alembic_version`, no
`phone` column anywhere. The chain above is built for exactly this state.
1. **Snapshot RDS** (manual snapshot) before anything.
2. Run migrations from a properly-authed context (the EB instance, or a host
   whose IP the RDS security group + MySQL `admin@host` grant allows — note a
   home IP was denied 2026-09-27).
3. `flask db upgrade` (applies the 3 migrations). MySQL DDL is non-transactional,
   so a failure can half-apply — the snapshot is the recovery path.
4. Verify: `alembic_version = b2f1c3a4d5e6`, SVDGC org present, existing players
   all `org_id=1`, one membership per user.
Re-run `scripts/prod_rehearsal.sh` locally anytime to re-validate the path.

### Follow-ups (deferred, not blocking Phase 1)
- **In-memory `rating_system` is not multi-tenant.** DG-Dubs serves reads from
  a process-global `TournamentRatingSystem` loaded once at boot. Phase 1 treats
  it as SVDGC's (Option A). Before onboarding a 2nd org, refactor it to be
  per-org (keyed by `org_id`, or built per-request) — otherwise orgs would
  share one rating cache. DG-Dubs *writes* already stamp `org_id` via the flush
  hook, so the DB is correctly owned; only the in-memory read cache is
  single-org.
- **Read call-site scoping.** Migrate tenant reads to `tenant_query` (or add a
  global scoped-session filter) when multi-org lands.
- **CRA → Vite** frontend migration before path-based deploy (see §8 Phase 2.5).
- **SQLAlchemy `Query.get()` legacy warnings** throughout Tags code — cleanup
  to `db.session.get()` at some point.

## 12. Appendix — Confirmed Inventory Snapshot (2026-09-27)

- Account 839087536917, region us-west-2.
- EB: `D-Rater/production` (e-9qqydjxwxi), `DG-Putt/dgputt-api` (e-wgcvyfa6pp).
- RDS: `dgputt-db`, MySQL 8.4, single-AZ, deletion-protection ON,
  publicly accessible, storage-encrypted (KMS).
- CloudFront: dg-rater.com, api.dg-rater.com, putt.dg-rater.com,
  api.putt.dg-rater.com. No tags.dg-rater.com yet.
- `production` env: SingleInstance t3.micro, `DB_NAME=dg_dubs`,
  `RESTORE_FROM_BACKUP=true`.
- `dgputt-api` env: `DB_NAME=dgputt`.
