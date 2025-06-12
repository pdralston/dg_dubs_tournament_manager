# Disc Golf League Tournament Rating System

A rating system for doubles disc golf leagues that tracks individual player contributions and predicts team performance in tournament-style play.

## Project Structure

This project is organized into two main components:

1. **Core Rating System** (`simple_approach/`): The core functionality for tracking player ratings, recording tournaments, and generating teams.

2. **Web Application** (`web_app/`): A Flask-based web interface for the rating system.

3. **Command-Line Interface** (`tournament_manager.py`): A CLI for interacting with the rating system.

## Features

- Track individual player ratings
- Calculate team ratings based on individual player skills
- Predict tournament outcomes and expected scores
- Update ratings based on actual vs. expected performance
- Generate balanced teams for league play
- Tournament history tracking
- Support for ghost players when there's an odd number of players
- Flexible storage options: SQLite database (default) or JSON

## Reliability Features

The system includes several reliability features to ensure data integrity:

### Case-Insensitive Player Lookups
- Player names are matched case-insensitively for all operations
- Original casing is preserved in the database and output
- This allows for more flexible user input (e.g., "player" vs "Player")

### Database Corruption Protection
- Automatic detection of invalid or corrupted database files
- Automatic backup creation before any potentially destructive operations
- Automatic recovery from JSON data when available
- Detailed error messages and warnings instead of crashes

### Robust Error Handling
- Graceful handling of database connection issues
- Continued operation even when database operations fail
- Safe transaction management with proper rollbacks

## How It Works

This system uses a modified Elo-style rating algorithm adapted for tournament play:

1. Each player has an individual rating (starting at 1000 by default)
   - When adding via CSV, a provided skill class of A or B sill seed the rating as 1300 or 1000 respectively 
2. Team ratings are calculated as the average of individual player ratings
3. Expected tournament positions are calculated based on team ratings
4. After each tournament, player ratings are updated based on:
   - The player's overall position
   - The difference between expected and actual positions
   - A K-factor that determines how quickly ratings change
   - The player's experience level (newer players' ratings change faster)

## Getting Started

### Prerequisites

- Python 3.6 or higher
- SQLite3 (included with Python)

### Installation

1. Clone this repository or download the files
2. Navigate to the project directory
3. Install the core package:

```bash
pip install -e ./tournament_core
```

4. For the web application create and activate a virtual environment:
```bash
python -m venv venv
./venv/Scripts/activate
```

If you are on a Windows machine you may need to set the execution policy:
```bash
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
.\venv\Scripts\activate
```
5. install additional dependencies:

```bash
pip install -r web_app/requirements.txt
```

### Command-Line Usage

The system provides a unified command-line interface with flexible storage options:

#### Add a new player

```bash
# Using database storage (default)
python tournament_manager.py add "Player Name" --rating 1000

# Using JSON storage
python tournament_manager.py --use-json add "Player Name" --rating 1000
```

#### Add multiple players from a file

```bash
# Using database storage (default)
python tournament_manager.py add --file players.csv

# Using JSON storage
python tournament_manager.py --use-json add --file players.csv
```

The players file should have one player per line in the format:
```
PlayerName,SkillClass
```
Where SkillClass is 'A' or 'B' ('A' players start with 1300 rating, 'B' with 1000)

#### List all players and their ratings

```bash
# Using database storage (default)
python tournament_manager.py list

# Using JSON storage
python tournament_manager.py --use-json list
```

#### Record a tournament result

You can record tournament results in two ways:

1. Interactive mode:
```bash
# Using database storage (default)
python tournament_manager.py record --course "Course Name" --date "YYYY-MM-DD"

# Using JSON storage
python tournament_manager.py --use-json record --course "Course Name" --date "YYYY-MM-DD"
```

2. From a file:
```bash
# Using database storage (default)
python tournament_manager.py record --file results.txt --course "Course Name" --date "YYYY-MM-DD"

# Using JSON storage
python tournament_manager.py --use-json record --file results.txt --course "Course Name" --date "YYYY-MM-DD"
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
# Using database storage (default)
python tournament_manager.py predict --par 54

# Using JSON storage
python tournament_manager.py --use-json predict --par 54
```

2. From a file:
```bash
# Using database storage (default)
python tournament_manager.py predict --file teams.txt --par 54

# Using JSON storage
python tournament_manager.py --use-json predict --file teams.txt --par 54
```

The teams file should have one team per line in the format:
```
Player1,Player2
```

#### View player details

```bash
# Using database storage (default)
python tournament_manager.py details "Player Name"

# Using JSON storage
python tournament_manager.py --use-json details "Player Name"
```

#### Generate balanced teams

```bash
# Using database storage (default)
python tournament_manager.py teams "Player1" "Player2" "Player3" "Player4" "Player5" "Player6" "Player7" "Player8"

# Using JSON storage
python tournament_manager.py --use-json teams "Player1" "Player2" "Player3" "Player4" "Player5" "Player6" "Player7" "Player8"
```

For odd numbers of players, use the `--allow-ghost` flag:

```bash
# Using database storage (default)
python tournament_manager.py teams "Player1" "Player2" "Player3" "Player4" "Player5" "Player6" "Player7" --allow-ghost

# Using JSON storage
python tournament_manager.py --use-json teams "Player1" "Player2" "Player3" "Player4" "Player5" "Player6" "Player7" --allow-ghost
```

#### View tournament history

```bash
# Using database storage (default)
python tournament_manager.py history --limit 5

# Using JSON storage
python tournament_manager.py --use-json history --limit 5
```

#### Switch storage mode

You can switch between database and JSON storage:

```bash
# Switch to JSON storage
python tournament_manager.py storage json

# Switch back to database storage
python tournament_manager.py --use-json storage db
```

### Web Application Usage

To run the web application:

```bash
cd web_app
python app.py
```

The application will be available at http://localhost:5000

## Data Storage

Player data and tournament history can be stored in two ways:

1. SQLite database (`tournament_data.db` by default) - This is the default storage method
2. JSON file (`tournament_data.json` by default) - Available as an alternative option

## Example Scripts

The project includes example scripts to demonstrate functionality:

- `example_tournament.sh` - Demonstrates basic tournament functionality
- `example_ghost_player.sh` - Demonstrates the ghost player feature for odd numbers of players
- `example_db_storage.sh` - Demonstrates switching between database and JSON storage

## Next Steps

Planned enhancements include:
- Web interface development
- Enhanced analytics
- Course-specific adjustments
- Mobile app integration
- Advanced features like handicap systems and player compatibility scores

## Customization

You can modify the rating system parameters in `tournament_core/tournament_ratings.py`:

- Adjust K-factors to change how quickly ratings update
- Modify the team rating calculation
- Change the expected position formula
- Adjust the score prediction model

Database behavior can be customized in `tournament_core/tournament_db_manager.py`:
- Configure backup file naming and locations
- Adjust error handling and reporting
- Modify recovery strategies

## License

This project is open source and available for any use.
