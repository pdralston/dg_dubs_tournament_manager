# DG-Dubs Tournament Manager + DG-Tags

A multi-app backend serving two disc golf league management applications — **DG-Dubs** (doubles tournament ratings) and **DG-Tags** (bag tag tracking) — under a shared Flask API deployed to a single Elastic Beanstalk instance.

**Live:** https://dg-rater.com (DG-Dubs) | https://tags.dg-rater.com (DG-Tags — in development)

## Architecture

```
tags.dg-rater.com                  dg-rater.com
      │                                 │
      ▼                                 ▼
┌──────────────┐               ┌──────────────┐
│ S3+CloudFront│               │ S3+CloudFront│
│ (DG-Tags SPA)│               │(DG-Dubs SPA) │
└──────┬───────┘               └──────┬───────┘
       │ /api/tags/*                   │ /api/players, etc.
       ▼                               ▼
┌─────────────────────────────────────────────┐
│       Flask API (Elastic Beanstalk)         │
│                                             │
│  DG-Dubs blueprints (/api/...)              │
│  DG-Tags blueprint  (/api/tags/...)         │
│  Shared auth (session-based, PBKDF2)        │
└───────────────────┬─────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────┐
│            MySQL (AWS RDS)                   │
│  DG-Dubs tables + DG-Tags tables            │
└─────────────────────────────────────────────┘
```

- **DG-Dubs Frontend** — React 19 + TypeScript (CRA) at `frontend/`
- **DG-Tags Frontend** — React 19 + TypeScript (CRA) at `tags-frontend/`
- **Backend** — Flask + SQLAlchemy + PyMySQL, app factory pattern
- **Database** — MySQL (AWS RDS), shared instance
- **Auth** — Session-based, roles: Admin / Director / Viewer

## Features

### DG-Dubs

- Player rating system (modified Elo for doubles tournaments)
- Balanced team generation for weekly events
- Tournament history with full result details
- Ace pot tracker with configurable cap
- Season archiving
- Payout tracking (seasonal and lifetime)

### DG-Tags

- **Event lifecycle management:** Pending → Scheduled → In Progress → Complete
- **Two event types:** Annual (tag pool 1..n) and Monthly (turned-in tag pool)
- **Tag distribution algorithm:** Score-based with old-tag tiebreaker, DNF handling
- **Tag inventory system:** Track total purchased, available, and lost/unavailable tags
- **Registration import:** Bulk import from DGScene CSV files
- **Score import:** CSV and XLSX file import with UDisc name matching + manual resolution
- **Non-player assignment:** Highest available from inventory for annual events
- **Same-day registration:** For monthly events with auto-tag-assignment from inventory
- **PII protection:** Write-blind pattern for directors, audit logging, separate table
- **Member search:** By name or UDisc name for quick registration

## Project Structure

```
dg_dubs_tournament_manager/
├── backend/
│   ├── app.py                      # Flask app factory (create_app)
│   ├── shared/
│   │   └── auth.py                 # AuthManager + decorators
│   ├── models/
│   │   ├── __init__.py             # Re-exports all models
│   │   ├── platform.py            # User, UserSession, PiiAccessLog
│   │   ├── dubs.py                # DG-Dubs domain models
│   │   └── tags.py                # TagMember, TagEvent, TagRegistration,
│   │                              #   TagHistory, TagInventory, TagUnavailable
│   ├── apps/
│   │   ├── dubs/
│   │   │   ├── routes/            # 6 route files
│   │   │   └── services/          # ratings, db_manager, ace_pot_manager
│   │   └── tags/
│   │       ├── routes.py          # 20 endpoints under /api/tags/
│   │       └── services.py        # Distribution algorithm, inventory,
│   │                              #   transitions, imports, matching
│   ├── requirements.txt
│   └── venv/
├── frontend/                       # DG-Dubs React app
│   ├── src/
│   │   ├── App.tsx
│   │   └── components/
│   └── package.json
├── tags-frontend/                  # DG-Tags React app (standalone)
│   ├── src/
│   │   ├── App.tsx                # App shell with tab navigation
│   │   ├── components/            # Standings, Events, Members, Inventory, Login
│   │   ├── context/AuthContext.tsx # Session auth provider
│   │   ├── services/api.ts       # Typed API client
│   │   └── types/index.ts        # TypeScript interfaces
│   └── package.json
├── tests/
│   ├── conftest.py                # Shared fixtures (SQLite in-memory, auth clients)
│   └── test_tags_lifecycle.py     # 50 tests across 8 classes
├── DG-Tags-Design.md              # DG-Tags requirements & design doc
├── application.py                 # AWS EB entry point
├── pytest.ini
└── .env.example
```

## Getting Started

### Prerequisites

- Python 3.12+
- Node.js 18+
- MySQL 8.0+ (local or AWS RDS)

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create `.env` at project root (see `.env.example`):
```
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=dg_dubs
ADMIN_USERNAME=admin
ADMIN_PASSWORD=change_me
SECRET_KEY=change-me-in-production
```

Run:
```bash
python app.py
# or from project root:
python application.py
```

API available at http://localhost:5000.

### DG-Dubs Frontend

```bash
cd frontend
npm install
npm start
```

Available at http://localhost:3000.

### DG-Tags Frontend

```bash
cd tags-frontend
cp .env.example .env   # edit REACT_APP_API_URL if needed
npm install
npm start
```

Available at http://localhost:3000 (run one frontend at a time, or change ports).

### Running Tests

```bash
source backend/venv/bin/activate
python -m pytest -v          # all 50 tests
python -m pytest --cov=backend  # with coverage
```

## DG-Tags API

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/tags/members` | — | List members |
| GET | `/api/tags/members/search?q=` | — | Search members |
| POST | `/api/tags/members/check-duplicate` | Director | Duplicate check |
| POST | `/api/tags/members` | Director | Create member |
| PUT | `/api/tags/members/<id>` | Director | Update member |
| DELETE | `/api/tags/members/<id>` | Admin | Deactivate + purge PII |
| POST | `/api/tags/members/<id>/assign-tag` | Director | Assign tag (outside event) |
| GET | `/api/tags/members/<id>/history` | — | Tag history |
| GET | `/api/tags/events` | — | List events |
| POST | `/api/tags/events` | Director | Create event |
| GET | `/api/tags/events/<id>` | — | Event details |
| POST | `/api/tags/events/<id>/register` | Director | Register player |
| POST | `/api/tags/events/<id>/register/import` | Director | Bulk import (CSV) |
| POST | `/api/tags/events/<id>/checkin` | Director | Check in player |
| PUT | `/api/tags/events/<id>/registrations/<rid>` | Director | Modify registration |
| POST | `/api/tags/events/<id>/transition` | Director | Advance status |
| POST | `/api/tags/events/<id>/scores` | Director | Submit scores |
| POST | `/api/tags/events/<id>/scores/import` | Director | Import scores (CSV/XLSX) |
| POST | `/api/tags/events/<id>/scores/resolve` | Director | Resolve ambiguities |
| GET | `/api/tags/standings` | — | Current standings |
| GET | `/api/tags/inventory?year=` | Director | Inventory status |
| POST | `/api/tags/inventory` | Admin | Set total tags |
| POST | `/api/tags/inventory/unavailable` | Admin | Mark tag lost |
| DELETE | `/api/tags/inventory/unavailable` | Admin | Restore tag |

## DG-Tags Event Lifecycle

```
Pending → Scheduled → In Progress → Complete
```

| Status | Visibility | Actions Available |
|--------|-----------|-------------------|
| Pending | Admin/TD only | Create event, register players (manual or CSV import) |
| Scheduled | All | Check-in, same-day registration, modify player↔non-player |
| In Progress | All | Enter scores (manual or import), resolve ambiguities |
| Complete | All | View results (read-only) |

### Transition Workflows

- **Pending → Scheduled:** Registration complete, event goes public
- **Scheduled → In Progress:** Non-players get tags (annual), unchecked players marked DNF
- **In Progress → Complete:** Distribution algorithm runs, history written, member tags updated

## Tag Distribution Algorithm

**Monthly:** Pool = turned-in tags from all players (including DNF)  
**Annual:** Pool = 1..n where n = checked-in player count

1. Separate finished players from DNF players
2. Sort finished by score ASC, old_tag ASC (tiebreaker)
3. DNF players get highest tags from pool, ordered by old_tag DESC
4. Remaining tags assigned to finished players (lowest tag → best score)

## DG-Dubs API

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/players` | — | List all players |
| POST | `/api/players` | Director | Add a player |
| GET | `/api/players/<name>` | — | Player details + history |
| DELETE | `/api/players/<name>` | Admin | Remove a player |
| GET | `/api/tournaments` | — | List tournaments |
| POST | `/api/tournaments/record` | Director | Record results |
| POST | `/api/tournaments/generate-teams` | Director | Generate teams |
| GET | `/api/ace-pot/balance` | — | Ace pot balance |
| POST | `/api/ace-pot/entries` | Director | Add entry |
| POST | `/api/auth/login` | — | Login |
| POST | `/api/auth/logout` | Auth | Logout |
| GET | `/api/auth/me` | Auth | Current user |
| POST | `/api/archive/season` | Admin | Archive season |

## Deployment

**Backend:** AWS Elastic Beanstalk (single instance serves both apps)  
**DG-Dubs Frontend:** S3 + CloudFront → `dg-rater.com`  
**DG-Tags Frontend:** S3 + CloudFront → `tags.dg-rater.com`  
**Database:** AWS RDS MySQL (shared)

Deploy frontend:
```bash
cd frontend && npm run build && aws s3 sync build/ s3://<dubs-bucket> --delete
cd tags-frontend && npm run build && aws s3 sync build/ s3://<tags-bucket> --delete
```

## Testing

50 tests covering the DG-Tags API lifecycle:

```
tests/test_tags_lifecycle.py
├── TestTagMemberManagement (14)     # CRUD, PII, search, duplicates
├── TestEventCreation (7)            # Types, visibility, validation
├── TestMonthlyEventLifecycle (4)    # Full workflow, tiebreaker, DNF, same-day
├── TestAnnualEventLifecycle (3)     # 1..n pool, non-player assignment, auto-DNF
├── TestStateTransitions (5)         # Invalid transitions, gating
├── TestInventoryManagement (8)      # Set/get, unavailable, assign
├── TestScoreImport (2)              # CSV matching, unmatched
├── TestRegistrationImport (2)       # DGScene CSV, state validation
└── TestStandingsAndHistory (4)      # Public access, sorting, history
```

## License

This project is open source. Consider supporting the developer: https://paypal.me/ralstontech
