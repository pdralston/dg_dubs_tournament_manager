# DG-Dubs Tournament Manager

A web application for managing a doubles disc golf league — tracking individual player ratings, recording tournaments, generating balanced teams, and managing an ace pot. Built with a React (TypeScript) frontend, Flask REST API backend, and MySQL database.

## Architecture

```
┌─────────────────────┐       ┌─────────────────────┐       ┌────────────────┐
│  React Frontend     │──────▶│  Flask API Backend   │──────▶│  MySQL (RDS)   │
│  (TypeScript)       │ HTTP  │  (Python)            │  SQL  │                │
│  Port 3000          │◀──────│  Port 5000           │◀──────│  Port 3306     │
└─────────────────────┘       └─────────────────────┘       └────────────────┘
```

- **Frontend** — React 19 + TypeScript, bootstrapped with Create React App
- **Backend** — Flask + Flask-SQLAlchemy + PyMySQL, session-based auth
- **Database** — MySQL (AWS RDS), schema managed via SQLAlchemy models
- **Legacy CLI** — `tournament_manager.py` still available for command-line use

## Features

### Player Management
- Add/remove players with initial ratings (A-class starts at 1300, B-class at 1000)
- View player list sorted by rating
- Player detail view with full tournament history and rating progression

### Tournament Management
- Record tournament results with team compositions, scores, and positions
- Elo-style rating updates based on expected vs. actual position
- Balanced team generation for upcoming rounds
- Ghost player support for odd participant counts
- Tournament history with full result details
- Payout tracking (seasonal and lifetime cash)

### Ace Pot Tracker
- Running ledger of ace pot contributions and payouts
- Configurable cap amount with current/reserve split
- Linked to tournaments and players

### Season Archiving
- Archive completed seasons to keep active data clean
- Historical season data preserved for reference

### Authentication & Authorization
- Role-based access: Admin, Director, Viewer (unauthenticated)
- Session-based auth with PBKDF2 password hashing
- Viewers can see players, ratings, and tournament history
- Directors can record tournaments and manage players
- Admins have full access including user management

## Project Structure

```
dg_dubs_tournament_manager/
├── frontend/                  # React TypeScript frontend
│   ├── src/
│   │   ├── App.tsx            # Main app with tab navigation
│   │   ├── components/
│   │   │   ├── PlayerList.tsx
│   │   │   ├── PlayerDetails.tsx
│   │   │   ├── Tournaments.tsx
│   │   │   ├── AcePotTracker.tsx
│   │   │   ├── Admin.tsx
│   │   │   └── Login.tsx
│   │   ├── config/api.ts      # API base URL config
│   │   └── types/index.ts     # TypeScript interfaces
│   └── package.json
├── backend/                   # Flask API backend
│   ├── app.py                 # Flask app entry point
│   ├── auth.py                # AuthManager + decorators
│   ├── api/
│   │   ├── players.py         # /api/players endpoints
│   │   ├── tournaments.py     # /api/tournaments endpoints
│   │   ├── ace_pot.py         # /api/ace-pot endpoints
│   │   ├── auth.py            # /api/auth endpoints
│   │   ├── archive.py         # /api/archive endpoints
│   │   └── storage.py         # /api/storage endpoints
│   └── requirements.txt
├── tournament_core/           # Shared Python package
│   ├── models.py              # SQLAlchemy models (Player, Tournament, Team, etc.)
│   ├── tournament_ratings.py  # Rating algorithm (Elo-style)
│   ├── tournament_db_manager.py
│   └── ace_pot_manager.py
├── database/
│   ├── create_tables.sql      # MySQL schema DDL
│   └── migrate_sqlite_to_mysql.py
├── tournament_manager.py      # Legacy CLI interface
├── create_admin.py            # Utility to create admin users
├── application.py             # AWS Elastic Beanstalk entry point
├── .ebextensions/             # EB configuration
├── .env.example               # Environment variable template
└── requirements.txt           # Root-level Python dependencies
```

## Getting Started

### Prerequisites

- Python 3.12+
- Node.js 18+
- MySQL 8.0+ (local or AWS RDS)

### Database Setup

1. Create a MySQL database:
```sql
CREATE DATABASE dg_dubs;
```

2. Optionally run the schema DDL (SQLAlchemy will also create tables on first run):
```bash
mysql -u root -p dg_dubs < database/create_tables.sql
```

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file in the project root (see `.env.example`):
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

Run the backend:
```bash
python app.py
```

The API will be available at http://localhost:5000.

### Frontend Setup

```bash
cd frontend
npm install
npm start
```

The frontend will be available at http://localhost:3000 and proxies API requests to the backend.

## API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/players` | — | List all players |
| POST | `/api/players` | Director | Add a player |
| GET | `/api/players/<name>` | — | Player details + history |
| DELETE | `/api/players/<name>` | Admin | Remove a player |
| GET | `/api/tournaments` | — | List tournaments |
| POST | `/api/tournaments/record` | Director | Record tournament results |
| POST | `/api/tournaments/generate-teams` | Director | Generate balanced teams |
| GET | `/api/ace-pot/balance` | — | Ace pot balance |
| POST | `/api/ace-pot/entries` | Director | Add ace pot entry |
| POST | `/api/auth/login` | — | Login |
| POST | `/api/auth/logout` | Auth | Logout |
| GET | `/api/auth/me` | Auth | Current user info |
| POST | `/api/archive/season` | Admin | Archive a season |

## Rating Algorithm

The system uses a modified Elo-style algorithm adapted for tournament play.

### Initial Ratings

- A-class players seed at 1300
- B-class players seed at 1000

### Team Rating

$$R_{team} = \frac{R_{player1} + R_{player2}}{2}$$

If one partner is a Ghost Player, the team rating equals the real player's rating.

### Expected Position

Teams are ranked by team rating (highest first). Equal-rated teams share an expected position.

### Rating Update Formula

After each tournament, every player's rating is updated:

$$R_{new} = R_{old} + K \cdot \left( \Delta_{pos} + M_{field} \right) \cdot B_{size}$$

Where:

**Position Differential** — how much better or worse the team performed vs. expectation:

$$\Delta_{pos} = E_{pos} - A_{pos}$$

- $E_{pos}$ = expected position (from team rating rank)
- $A_{pos}$ = actual finishing position

**Field Position Modifier** — a non-linear bonus/penalty based on where the team finished relative to the middle of the field:

$$midpoint = \frac{N}{2}$$

$$M_{field} = (midpoint - A_{pos}) \cdot \frac{|midpoint - A_{pos}|}{N - midpoint}$$

This amplifies the effect at the extremes (winning or finishing last counts more than finishing mid-pack).

**K-Factor** — controls the magnitude of rating change, decreasing as a player gains experience:

$$K = \begin{cases} 10 & \text{if } T < 5 \\ 5 & \text{if } 5 \leq T < 15 \\ 1 & \text{if } T \geq 15 \end{cases}$$

Where $T$ = total tournaments played (all-time).

**Tournament Size Bonus** — scales the adjustment so that larger fields produce larger rating swings:

$$B_{size} = 1 + (N - 4) \cdot 0.05$$

Where $N$ = number of teams in the event. A standard 4-team event has a multiplier of 1.0; an 8-team event has 1.2.

### Tie Handling

Teams with identical scores share the same position (standard competition ranking). Rating adjustments use that shared position for all tied teams.

## Team Matching Algorithm

### Overview

Players are sorted by rating (highest to lowest). The pairing strategy depends on field size:

- **> 6 players** — Top 3 are paired with bottom 3 (randomized), then remaining middle players are paired highest-with-lowest.
- **≤ 6 players** — All players are paired highest-with-lowest directly.
- **Odd player count** — A Ghost Player (rated at the field average) is appended to even out the field.

### Example: 10 Players (> 6 path)

```
Step 1: Sort by rating
┌──────────────────────────────────────────────────────────┐
│  1.Alice  2.Bob  3.Carol  4.Dan  5.Eve  6.Frank         │
│  (1400)   (1350) (1300)   (1200) (1150) (1100)          │
│                                                          │
│  7.Grace  8.Hank  9.Ivy  10.Jake                        │
│  (1050)   (1000)  (950)  (900)                           │
└──────────────────────────────────────────────────────────┘

Step 2: Extract top 3 (Pros) and bottom 3 (Ams)
┌─────────────────┐         ┌─────────────────┐
│  PROS           │         │  AMS            │
│  1. Alice (1400)│         │  8. Hank (1000) │
│  2. Bob   (1350)│         │  9. Ivy   (950) │
│  3. Carol (1300)│         │ 10. Jake  (900) │
└─────────────────┘         └─────────────────┘

Step 3: Shuffle Ams, then pair with Pros (1-to-1)
┌─────────────────────────────────────────────┐
│  Ams after shuffle: [Jake, Hank, Ivy]       │
│                                             │
│  Team A: Alice (1400) + Jake  (900)  = 1150 │
│  Team B: Bob   (1350) + Hank (1000)  = 1175 │
│  Team C: Carol (1300) + Ivy   (950)  = 1125 │
└─────────────────────────────────────────────┘

Step 4: Pair remaining middle players (highest ↔ lowest)
┌──────────────────────────────────────────────┐
│  Remaining: Dan(1200), Eve(1150),            │
│             Frank(1100), Grace(1050)         │
│                                              │
│  Team D: Dan   (1200) + Grace (1050) = 1125 │
│  Team E: Eve   (1150) + Frank (1100) = 1125 │
└──────────────────────────────────────────────┘
```

### Example: 6 Players (≤ 6 path)

```
Step 1: Sort by rating
┌───────────────────────────────────────────────┐
│  1.Alice  2.Bob  3.Carol  4.Dan  5.Eve  6.Frank │
│  (1400)   (1350) (1300)   (1100) (1000) (900)   │
└───────────────────────────────────────────────┘

Step 2: Pair highest ↔ lowest repeatedly
┌──────────────────────────────────────────────┐
│  Team A: Alice (1400) + Frank (900)  = 1150  │
│  Team B: Bob   (1350) + Eve  (1000)  = 1175  │
│  Team C: Carol (1300) + Dan  (1100)  = 1200  │
└──────────────────────────────────────────────┘
```

### Why randomize the bottom 3?

The top 3 vs. bottom 3 pairing uses a shuffle on the amateur group so that the highest-rated player doesn't *always* get paired with the lowest-rated player week after week. This adds variety while still guaranteeing that each top player is paired with a bottom player.

## Deployment

The application is configured for AWS Elastic Beanstalk deployment:
- `application.py` — EB entry point
- `.ebextensions/` — EB platform configuration
- Database: AWS RDS MySQL instance

## Legacy CLI

The original command-line interface is still available:

```bash
python tournament_manager.py list
python tournament_manager.py add "Player Name" --rating 1000
python tournament_manager.py record --course "Course Name" --date "2024-01-15"
python tournament_manager.py teams "Player1" "Player2" "Player3" "Player4"
```

## License

This project is open source and available for any use. Consider supporting the original developer: https://paypal.me/ralstontech.
