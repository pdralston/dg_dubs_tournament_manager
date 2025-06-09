# Disc Golf League Tournament Rating System - Web Application

This is the web interface for the Disc Golf League Tournament Rating System, providing a user-friendly way to manage players, tournaments, and team generation.

## Features

- View player ratings and tournament history
- Add new players with initial ratings
- Record tournament results
- Generate balanced teams for league play
- Switch between database and JSON storage
- Responsive design for mobile and desktop

## Getting Started

### Prerequisites

- Python 3.6 or higher
- Flask and dependencies (see requirements.txt)

### Installation

1. Clone this repository or download the files
2. Navigate to the project directory
3. Install the required dependencies:

```bash
pip install -r requirements.txt
```

### Running the Web Application

```bash
python app.py
```

The application will be available at http://localhost:5000

## Usage

### Home Page

The home page provides an overview of the system and quick links to the main features.

### Players

- **View Players**: See a list of all players and their current ratings
- **Player Details**: View a player's rating history and tournament performance
- **Add Player**: Add a new player with an initial rating

### Tournaments

- **View Tournaments**: See a list of all recorded tournaments and their results
- **Record Tournament**: Enter results for a new tournament

### Team Generation

- **Generate Teams**: Select players and create balanced teams for league play
- **View Predictions**: See expected positions and ratings for generated teams

### Storage Settings

- **Switch Storage Mode**: Choose between SQLite database and JSON file storage
- **View Current Storage**: See which storage method is currently in use

## Development

### Project Structure

- `app.py`: Main Flask application
- `tournament_ratings.py`: Core rating system logic
- `tournament_db_manager.py`: Database management
- `templates/`: HTML templates
- `static/`: CSS, JavaScript, and other static files

### Adding New Features

1. Add new routes to `app.py`
2. Create corresponding HTML templates in the `templates/` directory
3. Update CSS styles in `static/css/style.css` as needed

## License

This project is open source and available for any use.
