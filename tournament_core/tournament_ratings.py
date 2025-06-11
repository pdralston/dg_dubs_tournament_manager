#!/usr/bin/env python3
"""
Tournament-Style Disc Golf League Rating System

This script implements a rating system for a doubles disc golf league with flexible storage options.
It supports both SQLite database and JSON file storage.
"""

import json
import os
import sys
import datetime
import math
from collections.abc import Iterable
from typing import Dict, List, Tuple, Optional, Union, Any
from .tournament_db_manager import TournamentDBManager


class TournamentRatingSystem:
    def __init__(self, data_file: str = "tournament_data.db", use_db: bool = True):
        """
        Initialize the rating system with flexible storage options.
        
        Args:
            data_file: Path to the data file (database file if use_db=True, JSON file if use_db=False)
            use_db: Whether to use SQLite database (True) or JSON file (False) for storage
        """
        self.use_db = use_db
        self.db_file = "tournament_data.db" if use_db else None
        self.json_file = "tournament_data.json" if not use_db else None
        
        # Initialize data structures
        self.players = {}  # Player name -> rating data
        self.tournaments = []  # List of past tournaments
        
        # Initialize database manager if using database
        if self.use_db:
            try:
                self.db_manager = TournamentDBManager(self.db_file)
                self._load_from_db()
            except Exception as e:
                print(f"Error initializing database: {e}")
                print("Exiting due to database error.")
                sys.exit(1)
        else:
            self._load_from_json()
            
    def _create_case_insensitive_lookup(self) -> Dict[str, str]:
        """
        Create a case-insensitive lookup dictionary for player names.
        
        Returns:
            Dictionary mapping lowercase player names to their original casing
        """
        return {name.lower(): name for name in self.players.keys()}
        
    def _load_from_json(self) -> None:
        """Load player and tournament data from JSON file."""
        if os.path.exists(self.json_file):
            try:
                with open(self.json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.players = data.get('players', {})
                    self.tournaments = data.get('tournaments', [])
            except (json.JSONDecodeError, IOError, UnicodeDecodeError) as e:
                print(f"Error loading data from JSON: {e}")
                # Initialize with empty data
                self.players = {}
                self.tournaments = []
        else:
            # Initialize with empty data
            self.players = {}
            self.tournaments = []
            
    def _load_from_db(self) -> None:
        """Load player and tournament data from database."""
        # Load players
        players_data = self.db_manager.get_all_players()
        self.players = {}
        
        for player in players_data:
            name = player['name']
            self.players[name] = {
                'rating': player['rating'],
                'tournaments_played': player['tournaments_played'],
                'history': []
            }
            
            # Load player history
            history_entries = self.db_manager.get_player_history(name)
            for entry in history_entries:
                self.players[name]['history'].append({
                    'tournament_date': entry['tournament_date'],
                    'old_rating': entry['old_rating'],
                    'new_rating': entry['new_rating'],
                    'position': entry['position'],
                    'expected_position': entry['expected_position'],
                    'score': entry['score'],
                    'with_ghost': bool(entry['with_ghost']),
                    'change': entry['new_rating'] - entry['old_rating']
                })
                
        # Load tournaments
        tournaments_data = self.db_manager.get_tournaments()
        self.tournaments = []
        
        for tournament in tournaments_data:
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
                
            self.tournaments.append(tournament_data)
        
    def _save_to_json(self) -> None:
        """Save player and tournament data to JSON file."""
        try:
            data = {
                'players': self.players,
                'tournaments': self.tournaments
            }
            with open(self.json_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
            print(f"Data saved to {self.json_file}")
        except IOError as e:
            print(f"Error saving data to JSON: {e}")
            
    def _save_to_db(self) -> None:
        """Save player and tournament data to database."""
        try:
            # Export current data to JSON temporarily
            temp_json = "temp_export.json"
            data = {
                'players': self.players,
                'tournaments': self.tournaments
            }
            with open(temp_json, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
            
            # Import from the temporary JSON file to the database
            self.db_manager.import_from_json(temp_json)
            
            # Clean up temporary file
            try:
                os.remove(temp_json)
            except:
                pass
                
        except Exception as e:
            print(f"Error saving data to database: {e}")
            raise
            
    def save_data(self) -> None:
        """Save player and tournament data to the appropriate storage."""
        if self.use_db:
            try:
                self._save_to_db()
            except Exception as e:
                print(f"Error saving data to database: {e}")
                print("Exiting due to database error.")
                sys.exit(1)
        else:
            self._save_to_json()
            
    def player_exists(self, name: str) -> bool:
        """
        Check if a player exists (case-insensitive).
        
        Args:
            name: Player name to check
            
        Returns:
            True if player exists, False otherwise
        """
        player_lookup = self._create_case_insensitive_lookup()
        return name.lower() in player_lookup
        
    def get_player(self, name: str) -> Dict[str, Any]:
        """
        Get a player's data (case-insensitive).
        
        Args:
            name: Player name
            
        Returns:
            Player data dictionary
            
        Raises:
            ValueError: If player not found
        """
        player_lookup = self._create_case_insensitive_lookup()
        if name.lower() in player_lookup:
            original_name = player_lookup[name.lower()]
            return self.players[original_name]
        else:
            raise ValueError(f"Player {name} not found")
            
    def get_player_name(self, name: str) -> str:
        """
        Get a player's name with original casing (case-insensitive lookup).
        
        Args:
            name: Player name to look up
            
        Returns:
            Player name with original casing
            
        Raises:
            ValueError: If player not found
        """
        player_lookup = self._create_case_insensitive_lookup()
        if name.lower() in player_lookup:
            return player_lookup[name.lower()]
        else:
            raise ValueError(f"Player {name} not found")

    def add_player(self, name: str, initial_rating: int = 1000) -> None:
        """Add a new player to the system."""
        # Check if player exists (case-insensitive)
        if self.player_exists(name):
            print(f"Player {name} already exists.")
            return
            
        self.players[name] = {
            'rating': initial_rating,
            'tournaments_played': 0,
            'history': []
        }
        
        if self.use_db:
            try:
                self.db_manager.add_player(name, initial_rating)
            except Exception as e:
                print(f"Error adding player to database: {e}")
                print("Exiting due to database error.")
                sys.exit(1)
            
        print(f"Added player {name} with initial rating {initial_rating}")
        
    def get_k_factor(self, player: str) -> float:
        """
        Determine K-factor based on player experience.
        K-factor decreases as players play more tournaments.
        """
        # Get player with case-insensitive lookup
        player_data = self.get_player(player)
        tournaments_played = player_data['tournaments_played']
        
        if tournaments_played < 5:
            return 40  # New players - ratings change quickly
        elif tournaments_played < 15:
            return 32  # Intermediate players
        else:
            return 24  # Experienced players - ratings change more slowly
    
    def predict_tournament_outcome(self, teams: List[Tuple[str, str]]) -> Dict[Tuple[str, str], Dict[str, Any]]:
        """
        Predict the outcome of a tournament with multiple teams.
        
        Args:
            teams: List of (player1, player2) tuples representing teams
            
        Returns:
            Dictionary mapping teams to their predicted performance
        """
        # Calculate team ratings
        team_ratings = {}
        for team in teams:
            team_ratings[team] = self.calculate_team_rating(team[0], team[1])
            
        # Calculate expected positions
        expected_position = 1
        previous_rating = 0
        team_predictions = {}
        
        for team, rating in sorted(team_ratings.items(), key=lambda item:item[1], reverse=True):
            if previous_rating > rating:
                expected_position += 1
            previous_rating = rating
            team_predictions[team] = {
                'team': team,
                'rating': rating,
                'expected_position': expected_position
            }
            
        return team_predictions
    
    def record_tournament(self, team_results: List[Tuple[Tuple[str, str], int]],
                         course_name: str = None, date: str = None) -> None:
        """
        Record a tournament result and update ratings.
        
        Args:
            team_results: List of ((player1, player2), score) tuples, sorted by score (lowest first)
            course_name: Optional name of the course
            date: Optional date string (defaults to today)
        """
        if date is None:
            date = datetime.datetime.now().strftime("%Y-%m-%d")
            
        # Extract teams and verify all players exist
        teams = [team for team, _ in team_results]
        all_players = set()
        ghost_player_present = False
        
        for p1, p2 in teams:
            if p1 == "Ghost Player" or p2 == "Ghost Player":
                ghost_player_present = True
            else:
                all_players.add(p1)
                all_players.add(p2)
            
        # Check if all players exist (case-insensitive)
        for player in all_players:
            if not self.player_exists(player):
                raise ValueError(f"Player {player} not found")
                
        # Get predictions
        predictions = self.predict_tournament_outcome(teams)
        
        # Create tournament record
        tournament = {
            'date': date,
            'course': course_name,
            'teams': len(teams),
            'results': []
        }
        
        # Add tournament to database if using DB
        tournament_id = None
        if self.use_db:
            tournament_id = self.db_manager.add_tournament(date, course_name, len(teams))
            if tournament_id is None:
                print("Error: Failed to add tournament to database")
                return
        
        for position, (team, score) in self.resolve_tournament_positions(team_results):
            player1, player2 = team
            
            # Get original player names with correct casing
            if player1 != "Ghost Player":
                player1 = self.get_player_name(player1)
            if player2 != "Ghost Player":
                player2 = self.get_player_name(player2)
                
            team_rating = self.calculate_team_rating(player1, player2)
            expected_position = predictions[team]['expected_position']
            
            # Calculate performance rating
            # Performance is better when actual position is better than expected
            # (lower position number is better)
            position_diff = expected_position - position

            # Overall Position in the tournament adds an additional modifier
            # This addresses the issue of a top rated team maintaining 
            # pairings by their rating never changing, i.e. the "b" player
            # stagnating
            midpoint = len(teams) / 2
            max_diff = len(teams) - midpoint
            mid_diff = midpoint - position
            overall_modifier = (mid_diff) * abs(mid_diff / max_diff) 
            
            # Record team result
            team_result = {
                'team': [player1, player2],  # Use original casing
                'score': score,
                'position': position,
                'expected_position': expected_position,
                'team_rating': team_rating
            }
            tournament['results'].append(team_result)
            
            # Add team result to database if using DB
            if self.use_db and tournament_id is not None:
                team_id = self.db_manager.add_team_result(
                    tournament_id, player1, player2, position, 
                    expected_position, score, team_rating
                )
                if team_id is None:
                    print(f"Warning: Failed to add team result to database for {player1} & {player2}")
            
            # Update individual ratings - skip ghost player
            for player in [player1, player2]:
                if player == "Ghost Player":
                    continue
                    
                k_factor = self.get_k_factor(player)
                player_data = self.get_player(player)
                old_rating = player_data['rating']
                
                # Rating adjustment based on position difference
                # Normalize by number of teams to keep adjustments reasonable
                adjustment = k_factor * position_diff / len(teams)
                new_rating = old_rating + adjustment
                
                # Update player data
                player_data['rating'] = new_rating
                player_data['tournaments_played'] += 1
                
                history_entry = {
                    'tournament_date': date,
                    'old_rating': old_rating,
                    'new_rating': new_rating,
                    'change': new_rating - old_rating,
                    'position': position,
                    'expected_position': expected_position,
                    'score': score,
                    'with_ghost': "Ghost Player" in [player1, player2]
                }
                
                player_data['history'].append(history_entry)
                
                # Update player in database if using DB
                if self.use_db and tournament_id is not None:
                    rating_updated = self.db_manager.update_player_rating(player, new_rating)
                    tournaments_updated = self.db_manager.increment_player_tournaments(player)
                    history_added = self.db_manager.add_player_history(
                        player, tournament_id, old_rating, new_rating,
                        position, expected_position, score, "Ghost Player" in [player1, player2]
                    )
                    
                    if not rating_updated or not tournaments_updated or history_added is None:
                        print(f"Warning: Failed to update player data in database for {player}")
                
        # Add tournament to history
        self.tournaments.append(tournament)
        print(f"Tournament recorded with {len(teams)} teams")
        
        # Save data
        self.save_data()
        
    def resolve_tournament_positions(self, team_results: List[Tuple[Tuple[str, str], int]]) -> List[Tuple[int, Tuple[Tuple[str, str], int]]]:
        """
        Resolve tournament positions based on scores.
        
        Args:
            team_results: List of ((player1, player2), score) tuples
            
        Returns:
            List of (position, ((player1, player2), score)) tuples
        """
        # Sort by score (lowest first)
        sorted_results = sorted(team_results, key=lambda x: x[1])
        
        # Assign positions (handling ties)
        positions = []
        current_position = 1
        current_score = None
        
        for i, (team, score) in enumerate(sorted_results):
            if i == 0 or score != current_score:
                current_position = i + 1
                current_score = score
                
            positions.append((current_position, (team, score)))
            
        return positions
        
    def calculate_team_rating(self, player1: str, player2: str) -> float:
        """
        Calculate a team's rating based on individual player ratings.
        
        Args:
            player1: First player name
            player2: Second player name
            
        Returns:
            Team rating
        """
        # Handle ghost player
        if player1 == "Ghost Player":
            return self.get_player(player2)['rating']
        elif player2 == "Ghost Player":
            return self.get_player(player1)['rating']
            
        # Get player ratings (case-insensitive)
        player1_rating = self.get_player(player1)['rating']
        player2_rating = self.get_player(player2)['rating']
        
        # Calculate team rating (simple average)
        return (player1_rating + player2_rating) / 2
        
    def predict_scores(self, teams: List[Tuple[str, str]], par: int = 54) -> Dict[Tuple[str, str], float]:
        """
        Predict scores for a set of teams based on their ratings.
        
        Args:
            teams: List of (player1, player2) tuples representing teams
            par: Par score for the course
            
        Returns:
            Dictionary mapping teams to predicted scores
        """
        # Calculate team ratings
        team_ratings = {}
        for team in teams:
            team_ratings[team] = self.calculate_team_rating(team[0], team[1])
            
        # Calculate average rating
        avg_rating = sum(team_ratings.values()) / len(team_ratings)
        
        # Predict scores (higher rating = lower score)
        # We use a simple linear model where:
        # - Average rated team shoots par
        # - Each 10 rating points is worth 0.25 strokes
        predicted_scores = {}
        for team, rating in team_ratings.items():
            rating_diff = rating - avg_rating
            score_adjustment = -0.25 * (rating_diff / 10)  # Negative because higher rating = lower score
            predicted_scores[team] = par + score_adjustment
            
        return predicted_scores
        
    def switch_storage_mode(self, use_db: bool) -> None:
        """
        Switch between database and JSON storage.
        
        Args:
            use_db: True to use database, False to use JSON
        """
        if use_db == self.use_db:
            print(f"Already using {'database' if use_db else 'JSON'} storage.")
            return
            
        # Save current data in the current format
        self.save_data()
        
        # Switch mode
        self.use_db = use_db
        
        if use_db:
            # Initialize database manager if not already done
            self.db_file = "tournament_data.db"  # Set a default database file if switching to DB mode
            try:
                if not hasattr(self, 'db_manager'):
                    self.db_manager = TournamentDBManager(self.db_file)
                    
                # Import data from JSON to database
                self.db_manager.import_from_json(self.json_file)
                print(f"Switched to database storage ({self.db_file})")
            except Exception as e:
                print(f"Error switching to database storage: {e}")
                print("Exiting due to database error.")
                sys.exit(1)
        else:
            # Export data from database to JSON
            if hasattr(self, 'db_manager'):
                try:
                    self.db_manager.export_to_json(self.json_file)
                    print(f"Switched to JSON storage ({self.json_file})")
                except Exception as e:
                    print(f"Error switching to JSON storage: {e}")
                    print("Exiting due to database error.")
                    sys.exit(1)
            else:
                print(f"Switched to JSON storage ({self.json_file})")
                
    def generate_balanced_teams(self, players: List[str], allow_ghost: bool = False) -> List[Tuple[str, str]]:
        """
        Generate balanced teams from a list of players.
        
        Args:
            players: List of player names
            allow_ghost: Whether to allow a ghost player if there's an odd number of players
            
        Returns:
            List of (player1, player2) tuples representing teams
        """
        # Check if all players exist (case-insensitive)
        for player in players:
            if not self.player_exists(player):
                raise ValueError(f"Player {player} not found")
                
        # Get original player names with correct casing
        players = [self.get_player_name(player) for player in players]
        
        # Handle odd number of players
        if len(players) % 2 == 1:
            if allow_ghost:
                players.append("Ghost Player")
            else:
                raise ValueError("Odd number of players and ghost player not allowed")
                
        # Sort players by rating (highest to lowest)
        sorted_players = sorted(players, key=lambda p: self.get_player(p)['rating'] if p != "Ghost Player" else 0, reverse=True)
        
        # Create teams by pairing highest with lowest, second highest with second lowest, etc.
        teams = []
        while sorted_players:
            player1 = sorted_players.pop(0)  # Highest rated remaining player
            player2 = sorted_players.pop(-1) if sorted_players else "Ghost Player"  # Lowest rated remaining player
            teams.append((player1, player2))
            
        return teams
    def get_player_details(self, name: str) -> Dict[str, Any]:
        """
        Get detailed information about a player (case-insensitive).
        
        Args:
            name: Player name
            
        Returns:
            Dictionary with player details
            
        Raises:
            ValueError: If player not found
        """
        # Get player with case-insensitive lookup
        player_data = self.get_player(name)
        original_name = self.get_player_name(name)
        
        return {
            'name': original_name,
            'rating': player_data['rating'],
            'tournaments_played': player_data['tournaments_played'],
            'history': player_data['history']
        }
