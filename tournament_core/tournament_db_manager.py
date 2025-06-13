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
        try:
            self.create_tables()
        except Exception as e:
            print(f"Error initializing database: {e}")
            raise
        
    def connect(self) -> None:
        """Connect to the SQLite database."""
        try:
            if self.conn is not None:
                try:
                    # Test if connection is still valid
                    self.conn.execute("SELECT 1")
                    return  # Connection is still valid
                except (sqlite3.Error, sqlite3.ProgrammingError):
                    # Connection is invalid, close it
                    try:
                        self.close()
                    except:
                        pass
                        
            self.conn = sqlite3.connect(self.db_file)
            # Enable foreign keys
            self.conn.execute("PRAGMA foreign_keys = ON")
            # Return rows as dictionaries
            self.conn.row_factory = sqlite3.Row
        except sqlite3.Error as e:
            print(f"Database connection error: {e}")
            self.conn = None
            
    def close(self) -> None:
        """Close the database connection."""
        if self.conn:
            try:
                self.conn.close()
            except Exception as e:
                print(f"Error closing database connection: {e}")
            finally:
                self.conn = None
            
    def create_tables(self) -> None:
        """Create database tables if they don't exist."""
        self.connect()
        try:
            # Check if the file is a valid SQLite database
            try:
                self.conn.execute("SELECT 1 FROM sqlite_master LIMIT 1")
            except sqlite3.DatabaseError:
                # Not a valid database, create a backup and recreate
                self.close()
                if os.path.exists(self.db_file):
                    backup_file = f"{self.db_file}.backup"
                    print(f"WARNING: Invalid database file detected: {self.db_file}")
                    print(f"Creating backup at: {backup_file}")
                    try:
                        import shutil
                        shutil.copy2(self.db_file, backup_file)
                        print(f"Backup created successfully")
                    except Exception as e:
                        print(f"Error creating backup: {e}")
                    
                    # Try to recover data from JSON if available
                    json_file = "tournament_data.json"
                    if os.path.exists(json_file):
                        print(f"Found JSON data file. Will import data after database recreation.")
                        self.json_recovery_needed = True
                    
                    print(f"Removing invalid database file and creating a new one")
                    os.remove(self.db_file)
                self.connect()
                
            # Create tables
            self._create_tables()
            self.conn.commit()
            
            # After recreating the database, try to import data from JSON
            if hasattr(self, 'json_recovery_needed') and self.json_recovery_needed:
                self.close()  # Close the connection first
                json_file = "tournament_data.json"
                if os.path.exists(json_file):
                    try:
                        # Import the data
                        self.import_from_json(json_file)
                        print(f"Successfully recovered data from {json_file}")
                        delattr(self, 'json_recovery_needed')
                    except Exception as e:
                        print(f"Error recovering data from JSON: {e}")
                        
        except sqlite3.Error as e:
            print(f"Error creating tables: {e}")
            if self.conn:
                self.conn.rollback()
        finally:
            self.close()
            
    def _create_tables(self):
        """Create the database tables."""
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
                with_ghost BOOLEAN NOT NULL,
                FOREIGN KEY (player_id) REFERENCES players (id),
                FOREIGN KEY (tournament_id) REFERENCES tournaments (id)
            )
        ''')
            
    def add_player(self, name: str, rating: float) -> int:
        """
        Add a player to the database.
        
        Args:
            name: Player name
            rating: Initial rating
            
        Returns:
            Player ID
        """
        self.connect()
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT INTO players (name, rating, tournaments_played) VALUES (?, ?, ?)",
                (name, rating, 0)
            )
            player_id = cursor.lastrowid
            self.conn.commit()
            self.close()
            return player_id
        except sqlite3.IntegrityError:
            # Player already exists
            self.conn.rollback()
            self.close()
            raise ValueError(f"Player {name} already exists")
        except sqlite3.Error as e:
            print(f"Error adding player: {e}")
            if self.conn:
                self.conn.rollback()
            self.close()
            raise
            
    def update_player_rating(self, name: str, rating: float) -> bool:
        """
        Update a player's rating.
        
        Args:
            name: Player name
            rating: New rating
            
        Returns:
            True if successful, False otherwise
        """
        success = False
        try:
            self.connect()
            if not self.conn:
                print("Warning: Database connection failed in update_player_rating")
                return success
                
            self.conn.execute(
                "UPDATE players SET rating = ? WHERE name = ?",
                (rating, name)
            )
            self.conn.commit()
            success = True
        except sqlite3.Error as e:
            print(f"Error updating player rating: {e}")
            if self.conn:
                try:
                    self.conn.rollback()
                except:
                    pass
        finally:
            self.close()
            return success
            
    def increment_player_tournaments(self, name: str) -> bool:
        """
        Increment a player's tournaments played count.
        
        Args:
            name: Player name
            
        Returns:
            True if successful, False otherwise
        """
        success = False
        try:
            self.connect()
            if not self.conn:
                print("Warning: Database connection failed in increment_player_tournaments")
                return success
                
            self.conn.execute(
                "UPDATE players SET tournaments_played = tournaments_played + 1 WHERE name = ?",
                (name,)
            )
            self.conn.commit()
            success = True
        except sqlite3.Error as e:
            print(f"Error incrementing player tournaments: {e}")
            if self.conn:
                try:
                    self.conn.rollback()
                except:
                    pass
        finally:
            self.close()
            return success
            
    def get_player_id(self, name: str) -> int:
        """
        Get a player's ID by name.
        
        Args:
            name: Player name
            
        Returns:
            Player ID
        """
        self.connect()
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT id FROM players WHERE name = ?", (name,))
            result = cursor.fetchone()
            if result:
                player_id = result[0]
                self.close()
                return player_id
            else:
                self.close()
                raise ValueError(f"Player not found: {name}")
        except sqlite3.Error as e:
            print(f"Error getting player ID: {e}")
            self.close()
            raise
            
    def get_all_players(self) -> List[Dict[str, Any]]:
        """
        Get all players from the database.
        
        Returns:
            List of player dictionaries
        """
        result = []
        try:
            self.connect()
            if not self.conn:
                print("Warning: Database connection failed in get_all_players")
                return result
                
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM players ORDER BY rating DESC")
            result = [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            print(f"Error getting players: {e}")
        finally:
            self.close()
            return result
            
    def add_tournament(self, date: str, course: str, team_count: int) -> int:
        """
        Add a tournament to the database.
        
        Args:
            date: Tournament date
            course: Course name
            team_count: Number of teams
            
        Returns:
            Tournament ID
        """
        tournament_id = None
        try:
            self.connect()
            if not self.conn:
                print("Warning: Database connection failed in add_tournament")
                return tournament_id
                
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT INTO tournaments (date, course, team_count) VALUES (?, ?, ?)",
                (date, course, team_count)
            )
            tournament_id = cursor.lastrowid
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"Error adding tournament: {e}")
            if self.conn:
                try:
                    self.conn.rollback()
                except:
                    pass
        finally:
            self.close()
            return tournament_id
            
    def add_team_result(self, tournament_id: int, player1: str, player2: str,
                       position: int, expected_position: float,
                       score: int, team_rating: float) -> int:
        """
        Add a team result to the database.
        
        Args:
            tournament_id: Tournament ID
            player1: First player name
            player2: Second player name
            position: Actual position
            expected_position: Expected position
            score: Team score
            team_rating: Team rating
            
        Returns:
            Team ID
        """
        team_id = None
        try:
            self.connect()
            if not self.conn:
                print("Warning: Database connection failed in add_team_result")
                return team_id
                
            cursor = self.conn.cursor()
            
            # Get player IDs
            player1_id = self._get_player_id_safe(player1)
            player2_id = None
            if player2 != "Ghost Player":
                player2_id = self._get_player_id_safe(player2)
                
            if player1_id is None and player1 != "Ghost Player":
                print(f"Error: Player {player1} not found")
                return team_id
                
            # Special handling for ghost player
            if player1 == "Ghost Player":
                player1_id = -1  # Special ID for ghost player
                
            # Add team result
            cursor.execute(
                """INSERT INTO teams 
                   (tournament_id, player1_id, player2_id, position, expected_position, score, team_rating)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (tournament_id, player1_id, player2_id, position, expected_position, score, team_rating)
            )
            team_id = cursor.lastrowid
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"Error adding team result: {e}")
            if self.conn:
                try:
                    self.conn.rollback()
                except:
                    pass
        finally:
            self.close()
            return team_id
            
    def add_player_history(self, player_name: str, tournament_id: int,
                          old_rating: float, new_rating: float,
                          position: int, expected_position: float,
                          score: int, with_ghost: bool) -> int:
        """
        Add a player history entry to the database.
        
        Args:
            player_name: Player name
            tournament_id: Tournament ID
            old_rating: Old rating
            new_rating: New rating
            position: Actual position
            expected_position: Expected position
            score: Team score
            with_ghost: Whether the player played with a ghost player
            
        Returns:
            History entry ID
        """
        history_id = None
        try:
            self.connect()
            if not self.conn:
                print("Warning: Database connection failed in add_player_history")
                return history_id
                
            cursor = self.conn.cursor()
            
            # Get player ID
            player_id = self._get_player_id_safe(player_name)
            if player_id is None:
                print(f"Error: Player {player_name} not found")
                return history_id
                
            # Add history entry
            cursor.execute(
                """INSERT INTO player_history 
                   (player_id, tournament_id, old_rating, new_rating, position, 
                    expected_position, score, with_ghost)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (player_id, tournament_id, old_rating, new_rating, position, 
                 expected_position, score, with_ghost)
            )
            history_id = cursor.lastrowid
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"Error adding player history: {e}")
            if self.conn:
                try:
                    self.conn.rollback()
                except:
                    pass
        finally:
            self.close()
            return history_id
            
    def get_player_history(self, player_name: str) -> List[Dict[str, Any]]:
        """
        Get a player's history from the database.
        
        Args:
            player_name: Player name
            
        Returns:
            List of history entry dictionaries
        """
        result = []
        try:
            self.connect()
            if not self.conn:
                print("Warning: Database connection failed in get_player_history")
                return result
                
            cursor = self.conn.cursor()
            
            # Get player ID
            try:
                player_id = self._get_player_id_safe(player_name)
                if player_id is None:
                    return result
            except Exception:
                # Player not found
                return result
            
            # Get history entries
            cursor.execute(
                """SELECT ph.*, t.date as tournament_date
                   FROM player_history ph
                   JOIN tournaments t ON ph.tournament_id = t.id
                   WHERE ph.player_id = ?
                   ORDER BY t.date DESC""",
                (player_id,)
            )
            result = [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            print(f"Error getting player history: {e}")
        finally:
            self.close()
            return result
            
    def get_tournaments(self) -> List[Dict[str, Any]]:
        """
        Get all tournaments from the database with their results.
        
        Returns:
            List of tournament dictionaries with results
        """
        tournaments = []
        try:
            self.connect()
            if not self.conn:
                print("Warning: Database connection failed in get_tournaments")
                return tournaments
                
            cursor = self.conn.cursor()
            
            # Get tournaments
            cursor.execute("SELECT * FROM tournaments ORDER BY date DESC")
            tournaments = [dict(row) for row in cursor.fetchall()]
            
            # Get results for each tournament
            for tournament in tournaments:
                cursor.execute(
                    """SELECT t.*, p1.name as player1_name, p2.name as player2_name
                       FROM teams t
                       JOIN players p1 ON t.player1_id = p1.id
                       LEFT JOIN players p2 ON t.player2_id = p2.id
                       WHERE t.tournament_id = ?
                       ORDER BY t.position""",
                    (tournament['id'],)
                )
                tournament['results'] = [dict(row) for row in cursor.fetchall()]
                
                # Handle ghost players
                for result in tournament['results']:
                    if result['player2_name'] is None:
                        result['player2_name'] = "Ghost Player"
        except sqlite3.Error as e:
            print(f"Error getting tournaments: {e}")
        finally:
            self.close()
            return tournaments
            
    def import_from_json(self, json_file: str) -> None:
        """
        Import data from a JSON file into the database.
        
        Args:
            json_file: Path to the JSON file
        """
        try:
            # Check if JSON file exists
            if not os.path.exists(json_file):
                print(f"JSON file not found: {json_file}")
                return
                
            # Create a backup of the database before import
            if os.path.exists(self.db_file):
                backup_file = f"{self.db_file}.import_backup"
                try:
                    import shutil
                    shutil.copy2(self.db_file, backup_file)
                    print(f"Created database backup at: {backup_file}")
                except Exception as e:
                    print(f"Warning: Could not create database backup: {e}")
            
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Import players
            for name, player_data in data.get('players', {}).items():
                try:
                    self.connect()
                    cursor = self.conn.cursor()
                    cursor.execute(
                        "INSERT INTO players (name, rating, tournaments_played) VALUES (?, ?, ?)",
                        (name, player_data['rating'], player_data.get('tournaments_played', 0))
                    )
                    self.conn.commit()
                except sqlite3.IntegrityError:
                    # Player already exists, update rating
                    self.connect()
                    cursor = self.conn.cursor()
                    cursor.execute(
                        "UPDATE players SET rating = ?, tournaments_played = ? WHERE name = ?",
                        (player_data['rating'], player_data.get('tournaments_played', 0), name)
                    )
                    self.conn.commit()
                except Exception as e:
                    print(f"Error importing player {name}: {e}")
                finally:
                    self.close()
                    
            # Import tournaments
            for tournament in data.get('tournaments', []):
                # Add tournament
                try:
                    self.connect()
                    cursor = self.conn.cursor()
                    cursor.execute(
                        "INSERT INTO tournaments (date, course, team_count) VALUES (?, ?, ?)",
                        (tournament['date'], tournament.get('course'), tournament['teams'])
                    )
                    tournament_id = cursor.lastrowid
                    self.conn.commit()
                    self.close()
                    
                    # Add team results
                    for result in tournament['results']:
                        team = result['team']
                        player1, player2 = team[0], team[1]
                        
                        # Add players if they don't exist
                        for player in [p for p in team if p != "Ghost Player"]:
                            if player not in data['players']:
                                self.connect()
                                cursor = self.conn.cursor()
                                cursor.execute(
                                    "INSERT OR IGNORE INTO players (name, rating, tournaments_played) VALUES (?, ?, ?)",
                                    (player, 1000, 0)
                                )
                                self.conn.commit()
                                self.close()
                        
                        # Add team result
                        try:
                            self.connect()
                            cursor = self.conn.cursor()
                            
                            # Get player IDs safely
                            player1_id = self._get_player_id_safe(player1)
                            player2_id = None if player2 == "Ghost Player" else self._get_player_id_safe(player2)
                            
                            if player1_id is None:
                                print(f"Warning: Player {player1} not found, skipping result")
                                continue
                                
                            # Add team result
                            cursor.execute(
                                """INSERT INTO teams 
                                   (tournament_id, player1_id, player2_id, position, expected_position, score, team_rating)
                                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                                (tournament_id, player1_id, player2_id, result['position'], 
                                 result['expected_position'], result['score'], result['team_rating'])
                            )
                            self.conn.commit()
                        except sqlite3.Error as e:
                            print(f"Error adding team result: {e}")
                            if self.conn:
                                self.conn.rollback()
                        finally:
                            self.close()
                except Exception as e:
                    print(f"Error importing tournament {tournament.get('date')}: {e}")
                    
            print(f"Successfully imported data from {json_file}")
        except (json.JSONDecodeError, IOError, UnicodeDecodeError) as e:
            print(f"Error importing data from JSON: {e}")
        except Exception as e:
            print(f"Unexpected error during import: {e}")
            
    def _get_player_id_safe(self, name: str) -> Optional[int]:
        """
        Get a player's ID by name, without raising exceptions.
        
        Args:
            name: Player name
            
        Returns:
            Player ID or None if not found
        """
        # Special case for ghost player
        if name == "Ghost Player":
            # Return a special ID for ghost player
            # We don't actually store ghost players in the database
            return -1
            
        if not self.conn:
            return None
            
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT id FROM players WHERE name = ?", (name,))
            result = cursor.fetchone()
            return result[0] if result else None
        except sqlite3.Error as e:
            print(f"Error getting player ID for {name}: {e}")
            return None
            
    def export_to_json(self, json_file: str) -> None:
        """
        Export data from the database to a JSON file.
        
        Args:
            json_file: Path to the JSON file
        """
        try:
            # Get all players
            players = {}
            for player in self.get_all_players():
                name = player['name']
                players[name] = {
                    'rating': player['rating'],
                    'tournaments_played': player['tournaments_played'],
                    'history': []
                }
                
                # Get player history
                history = self.get_player_history(name)
                for entry in history:
                    players[name]['history'].append({
                        'tournament_date': entry['tournament_date'],
                        'old_rating': entry['old_rating'],
                        'new_rating': entry['new_rating'],
                        'change': entry['new_rating'] - entry['old_rating'],
                        'position': entry['position'],
                        'expected_position': entry['expected_position'],
                        'score': entry['score'],
                        'with_ghost': bool(entry['with_ghost'])
                    })
                    
            # Get all tournaments
            tournaments = []
            for tournament in self.get_tournaments():
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
                
            # Write to JSON file
            data = {
                'players': players,
                'tournaments': tournaments
            }
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
                
            print(f"Successfully exported data to {json_file}")
        except Exception as e:
            print(f"Error exporting data to JSON: {e}")
            raise
