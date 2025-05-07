# Disc Golf League Tournament Rating System

A rating system for doubles disc golf leagues that tracks individual player contributions and predicts team performance in tournament-style play.

## Features

- Track individual player ratings
- Calculate team ratings based on individual player skills
- Predict tournament outcomes and expected scores
- Update ratings based on actual vs. expected performance
- Generate balanced teams for league play
- Tournament history tracking
- Support for ghost players when there's an odd number of players
- Optional SQLite database storage for improved data management

## How It Works

This system uses a modified Elo-style rating algorithm adapted for tournament play:

1. Each player has an individual rating (starting at 1000 by default)
2. Team ratings are calculated as the average of individual player ratings
3. Expected tournament positions are calculated based on team ratings
4. After each tournament, player ratings are updated based on:
   - The difference between expected and actual positions
   - A K-factor that determines how quickly ratings change
   - The player's experience level (newer players' ratings change faster)

## Getting Started

### Prerequisites

- Python 3.6 or higher
- SQLite3 (optional, for database storage)

### Installation

1. Clone this repository or download the files
2. Navigate to the project directory

### Usage

The system provides two command-line interfaces:

1. `tournament_manager.py` - Original JSON-based storage
2. `tournament_manager_db.py` - With optional SQLite database support

#### Add a new player

```bash
# Using JSON storage (default)
python tournament_manager.py add "Player Name" --rating 1000

# Using database storage
python tournament_manager_db.py --use-db add "Player Name" --rating 1000
```

#### List all players and their ratings

```bash
# Using JSON storage
python tournament_manager.py list

# Using database storage
python tournament_manager_db.py --use-db list
```

#### Record a tournament result

You can record tournament results in two ways:

1. Interactive mode:
```bash
# Using JSON storage
python tournament_manager.py record --course "Course Name" --date "YYYY-MM-DD"

# Using database storage
python tournament_manager_db.py --use-db record --course "Course Name" --date "YYYY-MM-DD"
```

2. From a file:
```bash
# Using JSON storage
python tournament_manager.py record --file results.txt --course "Course Name" --date "YYYY-MM-DD"

# Using database storage
python tournament_manager_db.py --use-db record --file results.txt --course "Course Name" --date "YYYY-MM-DD"
```

The results file should have one team per line in the format:
```
Player1,Player2,Score
```
Teams should be listed in order of finish (lowest score first).

#### Predict a tournament outcome

You can predict tournament outcomes in two ways:

1. Interactive mode:
```bash
# Using JSON storage
python tournament_manager.py predict --par 54

# Using database storage
python tournament_manager_db.py --use-db predict --par 54
```

2. From a file:
```bash
# Using JSON storage
python tournament_manager.py predict --file teams.txt --par 54

# Using database storage
python tournament_manager_db.py --use-db predict --file teams.txt --par 54
```

The teams file should have one team per line in the format:
```
Player1,Player2
```

#### View player details

```bash
# Using JSON storage
python tournament_manager.py details "Player Name"

# Using database storage
python tournament_manager_db.py --use-db details "Player Name"
```

#### Generate balanced teams

```bash
# Using JSON storage
python tournament_manager.py teams "Player1" "Player2" "Player3" "Player4" "Player5" "Player6" "Player7" "Player8"

# Using database storage
python tournament_manager_db.py --use-db teams "Player1" "Player2" "Player3" "Player4" "Player5" "Player6" "Player7" "Player8"
```

For odd numbers of players, use the `--allow-ghost` flag:

```bash
# Using JSON storage
python tournament_manager.py teams "Player1" "Player2" "Player3" "Player4" "Player5" "Player6" "Player7" --allow-ghost

# Using database storage
python tournament_manager_db.py --use-db teams "Player1" "Player2" "Player3" "Player4" "Player5" "Player6" "Player7" --allow-ghost
```

#### View tournament history

```bash
# Using JSON storage
python tournament_manager.py history --limit 5

# Using database storage
python tournament_manager_db.py --use-db history --limit 5
```

#### Switch storage mode

You can switch between JSON and database storage:

```bash
# Switch to database storage
python tournament_manager_db.py storage db

# Switch back to JSON storage
python tournament_manager_db.py --use-db storage json
```

## Data Storage

Player data and tournament history can be stored in two ways:

1. JSON file (`tournament_data.json` by default) in the project directory
2. SQLite database (`tournament_data.db` by default) for improved data management

## Example Scripts

The project includes example scripts to demonstrate functionality:

- `example_tournament.sh` - Demonstrates basic tournament functionality
- `example_ghost_player.sh` - Demonstrates the ghost player feature for odd numbers of players
- `example_db_storage.sh` - Demonstrates switching between JSON and database storage

## Next Steps

Planned enhancements include:
- Web interface development
- Enhanced analytics
- Course-specific adjustments
- Mobile app integration
- Advanced features like handicap systems and player compatibility scores

## Customization

You can modify the rating system parameters in `tournament_ratings.py` or `tournament_ratings_db.py`:

- Adjust K-factors to change how quickly ratings update
- Modify the team rating calculation
- Change the expected position formula
- Adjust the score prediction model

## License

This project is open source and available for any use.
