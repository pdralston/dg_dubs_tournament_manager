#!/usr/bin/env python3
"""
Tournament Database Manager

This module provides SQLite database functionality for the tournament rating system.
It handles database creation, connection, and all CRUD operations.
"""

import sqlite3
import json
import os
from typing import Dict, List, Tuple, Optional, Union, Any


class TournamentDBManager:
    def __init__(self, db_file: str = "tournament_data.db"):
        """Initialize the database manager."""
        self.db_file = db_file
        self.conn = None
        self.create_tables()
        
    def connect(self) -> None:
        """Connect to the SQLite database."""
        try:
            self.conn = sqlite3.connect(self.db_file)
            # Enable foreign keys
            self.conn.execute("PRAGMA foreign_keys = ON")
            # Return rows as dictionaries
            self.conn.row_factory = sqlite3.Row
        except sqlite3.Error as e:
            print(f"Database connection error: {e}")
            raise
            
    def close(self) -> None:
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
            
    def create_tables(self) -> None:
        """Create database tables if they don't exist."""
        self.connect()
        try:
            # Players table
            self.conn.execute('''
                CREATE TABLE IF NOT EXISTS players (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    rating REAL NOT NULL,
                    tournaments_played INTEGER NOT NULL DEFAULT 0
                )
            ''')
            
            # Tournaments table
            self.conn.execute('''
                CREATE TABLE IF NOT EXISTS tournaments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    course TEXT,
                    team_count INTEGER NOT NULL
                )
            ''')
            
            # Teams table
            self.conn.execute('''
                CREATE TABLE IF NOT EXISTS teams (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tournament_id INTEGER NOT NULL,
                    player1_id INTEGER NOT NULL,
                    player2_id INTEGER,  -- Can be NULL for ghost player
                    position INTEGER NOT NULL,
                    expected_position REAL NOT NULL,
                    score INTEGER NOT NULL,
                    team_rating REAL NOT NULL,
                    FOREIGN KEY (tournament_id) REFERENCES tournaments (id),
                    FOREIGN KEY (player1_id) REFERENCES players (id),
                    FOREIGN KEY (player2_id) REFERENCES players (id)
                )
            ''')
            
            # Player history table
            self.conn.execute('''
                CREATE TABLE IF NOT EXISTS player_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    player_id INTEGER NOT NULL,
                    tournament_id INTEGER NOT NULL,
                    old_rating REAL NOT NULL,
                    new_rating REAL NOT NULL,
                    position INTEGER NOT NULL,
                    expected_position REAL NOT NULL,
                    score INTEGER NOT NULL,
                    with_ghost BOOLEAN NOT NULL DEFAULT 0,
                    FOREIGN KEY (player_id) REFERENCES players (id),
                    FOREIGN KEY (tournament_id) REFERENCES tournaments (id)
                )
            ''')
            
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"Error creating tables: {e}")
            raise
        finally:
            self.close()
            
    def add_player(self, name: str, rating: float) -> int:
        """
        Add a new player to the database.
        
        Args:
            name: Player name
            rating: Initial rating
            
        Returns:
            Player ID
        """
        self.connect()
        try:
            cursor = self.conn.execute(
                "INSERT INTO players (name, rating, tournaments_played) VALUES (?, ?, 0)",
                (name, rating)
            )
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            print(f"Player {name} already exists.")
            cursor = self.conn.execute("SELECT id FROM players WHERE name = ?", (name,))
            return cursor.fetchone()[0]
        except sqlite3.Error as e:
            print(f"Error adding player: {e}")
            raise
        finally:
            self.close()
            
    def get_player(self, name: str) -> Dict[str, Any]:
        """
        Get player data by name.
        
        Args:
            name: Player name
            
        Returns:
            Player data dictionary or None if not found
        """
        self.connect()
        try:
            cursor = self.conn.execute(
                "SELECT id, name, rating, tournaments_played FROM players WHERE name = ?",
                (name,)
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
        except sqlite3.Error as e:
            print(f"Error getting player: {e}")
            raise
        finally:
            self.close()
            
    def get_player_by_id(self, player_id: int) -> Dict[str, Any]:
        """
        Get player data by ID.
        
        Args:
            player_id: Player ID
            
        Returns:
            Player data dictionary or None if not found
        """
        self.connect()
        try:
            cursor = self.conn.execute(
                "SELECT id, name, rating, tournaments_played FROM players WHERE id = ?",
                (player_id,)
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
        except sqlite3.Error as e:
            print(f"Error getting player: {e}")
            raise
        finally:
            self.close()
            
    def update_player_rating(self, name: str, new_rating: float) -> None:
        """
        Update a player's rating.
        
        Args:
            name: Player name
            new_rating: New rating value
        """
        self.connect()
        try:
            self.conn.execute(
                "UPDATE players SET rating = ? WHERE name = ?",
                (new_rating, name)
            )
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"Error updating player rating: {e}")
            raise
        finally:
            self.close()
            
    def increment_player_tournaments(self, name: str) -> None:
        """
        Increment a player's tournaments_played count.
        
        Args:
            name: Player name
        """
        self.connect()
        try:
            self.conn.execute(
                "UPDATE players SET tournaments_played = tournaments_played + 1 WHERE name = ?",
                (name,)
            )
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"Error incrementing player tournaments: {e}")
            raise
        finally:
            self.close()
            
    def get_all_players(self) -> List[Dict[str, Any]]:
        """
        Get all players from the database.
        
        Returns:
            List of player dictionaries
        """
        self.connect()
        try:
            cursor = self.conn.execute(
                "SELECT id, name, rating, tournaments_played FROM players"
            )
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            print(f"Error getting all players: {e}")
            raise
        finally:
            self.close()
            
    def add_tournament(self, date: str, course: str, team_count: int) -> int:
        """
        Add a new tournament to the database.
        
        Args:
            date: Tournament date
            course: Course name
            team_count: Number of teams
            
        Returns:
            Tournament ID
        """
        self.connect()
        try:
            cursor = self.conn.execute(
                "INSERT INTO tournaments (date, course, team_count) VALUES (?, ?, ?)",
                (date, course, team_count)
            )
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            print(f"Error adding tournament: {e}")
            raise
        finally:
            self.close()
            
    def add_team_result(self, tournament_id: int, player1: str, player2: str, 
                       position: int, expected_position: float, score: int, 
                       team_rating: float) -> int:
        """
        Add a team result to the database.
        
        Args:
            tournament_id: Tournament ID
            player1: First player name
            player2: Second player name (or "Ghost Player")
            position: Actual position (1-indexed)
            expected_position: Expected position
            score: Team score
            team_rating: Team rating
            
        Returns:
            Team ID
        """
        self.connect()
        try:
            # Get player IDs
            player1_id = self.get_player(player1)['id']
            player2_id = None if player2 == "Ghost Player" else self.get_player(player2)['id']
            
            cursor = self.conn.execute(
                """
                INSERT INTO teams 
                (tournament_id, player1_id, player2_id, position, expected_position, score, team_rating)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (tournament_id, player1_id, player2_id, position, expected_position, score, team_rating)
            )
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            print(f"Error adding team result: {e}")
            raise
        finally:
            self.close()
            
    def add_player_history(self, player_name: str, tournament_id: int, old_rating: float,
                          new_rating: float, position: int, expected_position: float,
                          score: int, with_ghost: bool) -> int:
        """
        Add a player history entry.
        
        Args:
            player_name: Player name
            tournament_id: Tournament ID
            old_rating: Old rating before tournament
            new_rating: New rating after tournament
            position: Actual position
            expected_position: Expected position
            score: Team score
            with_ghost: Whether player played with ghost player
            
        Returns:
            History entry ID
        """
        self.connect()
        try:
            player_id = self.get_player(player_name)['id']
            
            cursor = self.conn.execute(
                """
                INSERT INTO player_history 
                (player_id, tournament_id, old_rating, new_rating, position, 
                expected_position, score, with_ghost)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (player_id, tournament_id, old_rating, new_rating, position, 
                expected_position, score, 1 if with_ghost else 0)
            )
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            print(f"Error adding player history: {e}")
            raise
        finally:
            self.close()
            
    def get_player_history(self, player_name: str) -> List[Dict[str, Any]]:
        """
        Get history entries for a player.
        
        Args:
            player_name: Player name
            
        Returns:
            List of history entry dictionaries
        """
        self.connect()
        try:
            player = self.get_player(player_name)
            if not player:
                return []
                
            cursor = self.conn.execute(
                """
                SELECT ph.*, t.date as tournament_date, t.course
                FROM player_history ph
                JOIN tournaments t ON ph.tournament_id = t.id
                WHERE ph.player_id = ?
                ORDER BY t.date DESC
                """,
                (player['id'],)
            )
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            print(f"Error getting player history: {e}")
            raise
        finally:
            self.close()
            
    def get_tournaments(self, limit: int = None) -> List[Dict[str, Any]]:
        """
        Get all tournaments with their results.
        
        Args:
            limit: Optional limit on number of tournaments to return
            
        Returns:
            List of tournament dictionaries with results
        """
        self.connect()
        try:
            # Get tournaments
            query = "SELECT * FROM tournaments ORDER BY date DESC"
            if limit:
                query += f" LIMIT {limit}"
                
            cursor = self.conn.execute(query)
            tournaments = [dict(row) for row in cursor.fetchall()]
            
            # Get results for each tournament
            for tournament in tournaments:
                cursor = self.conn.execute(
                    """
                    SELECT t.*, 
                           p1.name as player1_name, 
                           IFNULL(p2.name, 'Ghost Player') as player2_name
                    FROM teams t
                    JOIN players p1 ON t.player1_id = p1.id
                    LEFT JOIN players p2 ON t.player2_id = p2.id
                    WHERE t.tournament_id = ?
                    ORDER BY t.position
                    """,
                    (tournament['id'],)
                )
                tournament['results'] = [dict(row) for row in cursor.fetchall()]
                
            return tournaments
        except sqlite3.Error as e:
            print(f"Error getting tournaments: {e}")
            raise
        finally:
            self.close()
            
    def import_from_json(self, json_file: str) -> None:
        """
        Import data from a JSON file into the database.
        
        Args:
            json_file: Path to JSON file
        """
        if not os.path.exists(json_file):
            print(f"JSON file not found: {json_file}")
            return
            
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
                
            # Import players
            for name, player_data in data.get('players', {}).items():
                player_id = self.add_player(name, player_data['rating'])
                
                # Update tournaments_played
                self.connect()
                self.conn.execute(
                    "UPDATE players SET tournaments_played = ? WHERE id = ?",
                    (player_data['tournaments_played'], player_id)
                )
                self.conn.commit()
                self.close()
                
            # Import tournaments
            for tournament_data in data.get('tournaments', []):
                date = tournament_data['date']
                course = tournament_data.get('course')
                team_count = tournament_data['teams']
                
                tournament_id = self.add_tournament(date, course, team_count)
                
                # Import results
                for i, result in enumerate(tournament_data['results'], 1):
                    team = result['team']
                    player1, player2 = team
                    position = result['position']
                    expected_position = result['expected_position']
                    score = result['score']
                    team_rating = result['team_rating']
                    
                    self.add_team_result(
                        tournament_id, player1, player2, position, 
                        expected_position, score, team_rating
                    )
                    
            # Import player history
            for name, player_data in data.get('players', {}).items():
                for history in player_data.get('history', []):
                    # Find the tournament ID
                    self.connect()
                    cursor = self.conn.execute(
                        "SELECT id FROM tournaments WHERE date = ?",
                        (history['tournament_date'],)
                    )
                    tournament_row = cursor.fetchone()
                    self.close()
                    
                    if tournament_row:
                        tournament_id = tournament_row['id']
                        self.add_player_history(
                            name, tournament_id, history['old_rating'], 
                            history['new_rating'], history['position'],
                            history['expected_position'], history['score'],
                            history.get('with_ghost', False)
                        )
                        
            print(f"Successfully imported data from {json_file}")
            
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error importing from JSON: {e}")
            
    def export_to_json(self, json_file: str) -> None:
        """
        Export database data to a JSON file.
        
        Args:
            json_file: Path to JSON file
        """
        try:
            # Get all players
            players = {}
            all_players = self.get_all_players()
            
            for player in all_players:
                name = player['name']
                players[name] = {
                    'rating': player['rating'],
                    'tournaments_played': player['tournaments_played'],
                    'history': []
                }
                
                # Get player history
                history_entries = self.get_player_history(name)
                for entry in history_entries:
                    players[name]['history'].append({
                        'tournament_date': entry['tournament_date'],
                        'old_rating': entry['old_rating'],
                        'new_rating': entry['new_rating'],
                        'position': entry['position'],
                        'expected_position': entry['expected_position'],
                        'score': entry['score'],
                        'with_ghost': bool(entry['with_ghost'])
                    })
                    
            # Get all tournaments
            tournaments = []
            all_tournaments = self.get_tournaments()
            
            for tournament in all_tournaments:
                tournament_data = {
                    'date': tournament['date'],
                    'course': tournament['course'],
                    'teams': tournament['team_count'],
                    'results': []
                }
                
                # Format results
                for result in tournament['results']:
                    tournament_data['results'].append({
                        'team': [result['player1_name'], result['player2_name']],
                        'position': result['position'],
                        'expected_position': result['expected_position'],
                        'score': result['score'],
                        'team_rating': result['team_rating']
                    })
                    
                tournaments.append(tournament_data)
                
            # Create final data structure
            data = {
                'players': players,
                'tournaments': tournaments
            }
            
            # Write to file
            with open(json_file, 'w') as f:
                json.dump(data, f, indent=2)
                
            print(f"Successfully exported data to {json_file}")
            
        except (IOError, sqlite3.Error) as e:
            print(f"Error exporting to JSON: {e}")


def main():
    """Simple demonstration of the database manager."""
    db_manager = TournamentDBManager()
    
    # Import from existing JSON file if it exists
    json_file = "tournament_data.json"
    if os.path.exists(json_file):
        print(f"Importing data from {json_file}...")
        db_manager.import_from_json(json_file)
        
    # Show all players
    players = db_manager.get_all_players()
    print("\nPlayers in database:")
    for player in players:
        print(f"{player['name']}: {player['rating']}")
        
    # Show tournaments
    tournaments = db_manager.get_tournaments()
    print(f"\nFound {len(tournaments)} tournaments in database")
    
    # Export back to JSON
    export_file = "tournament_data_export.json"
    print(f"\nExporting data to {export_file}...")
    db_manager.export_to_json(export_file)


if __name__ == "__main__":
    main()
