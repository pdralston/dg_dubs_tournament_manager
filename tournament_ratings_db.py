#!/usr/bin/env python3
"""
Tournament-Style Disc Golf League Rating System with SQLite Support

This script extends the tournament rating system to optionally use SQLite for data storage.
"""

import json
import os
import datetime
import math
from _collections_abc import Iterable
from typing import Dict, List, Tuple, Optional, Union, Any
from tournament_db_manager import TournamentDBManager

class TournamentRatingSystemDB:
    def __init__(self, db_file: str = "tournament_data.db", use_db: bool = True):
        """
        Initialize the rating system with database support.
        
        Args:
            db_file: Path to the SQLite database file
            use_db: Whether to use the database (True) or JSON (False)
        """
        self.use_db = use_db
        self.db_file = db_file
        self.json_file = "tournament_data.json"
        
        # Initialize data structures
        self.players = {}  # Player name -> rating data
        self.tournaments = []  # List of past tournaments
        
        # Initialize database manager if using database
        if self.use_db:
            self.db_manager = TournamentDBManager(db_file)
            self._load_from_db()
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
        """Load player and tournament data from JSON file if it exists."""
        if os.path.exists(self.json_file):
            try:
                with open(self.json_file, 'r') as f:
                    data = json.load(f)
                    self.players = data.get('players', {})
                    self.tournaments = data.get('tournaments', [])
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading data from JSON: {e}")
                # Initialize with empty data
                self.players = {}
                self.tournaments = []
                
    def _load_from_db(self) -> None:
        """Load player and tournament data from database."""
        try:
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
                        'with_ghost': bool(entry['with_ghost'])
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
                
        except Exception as e:
            print(f"Error loading data from database: {e}")
            # Initialize with empty data
            self.players = {}
            self.tournaments = []
        
    def _save_to_json(self) -> None:
        """Save player and tournament data to JSON file."""
        data = {
            'players': self.players,
            'tournaments': self.tournaments
        }
        try:
            with open(self.json_file, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"Data saved to {self.json_file}")
        except IOError as e:
            print(f"Error saving data to JSON: {e}")
            
    def _save_to_db(self) -> None:
        """Save player and tournament data to database."""
        try:
            # Export current data to JSON temporarily
            temp_json = "temp_export.json"
            self._save_to_json()
            
            # Import from the temporary JSON file to the database
            self.db_manager.import_from_json(self.json_file)
            
        except Exception as e:
            print(f"Error saving data to database: {e}")
            
    def save_data(self) -> None:
        """Save player and tournament data to the appropriate storage."""
        if self.use_db:
            self._save_to_db()
        else:
            self._save_to_json()
    
    def add_player(self, name: str, initial_rating: int = 1000) -> None:
        """Add a new player to the system."""
        if name in self.players:
            print(f"Player {name} already exists.")
            return
            
        self.players[name] = {
            'rating': initial_rating,
            'tournaments_played': 0,
            'history': []
        }
        
        if self.use_db:
            self.db_manager.add_player(name, initial_rating)
            
        print(f"Added player {name} with initial rating {initial_rating}")
        
    def get_ghost_player_rating(self) -> float:
        """
        Calculate an appropriate rating for a shost player based on the average of all players.

        Returns:
            Ghost player rating
        """
        if not self.players:
            return 1000 # Default rating if no players exist
        
        # Calculate average rating of all players
        total_rating = sum(player['rating'] for player in self.players.values())
        return total_rating/len(self.players)

    def player_exists(self, name: str) -> bool:
        """
        Check if player exists (case-insensitive).
        Args:
            name: Player name to check
        Returns:
            True if player exists, False otherwise.
        """
        if name == "Ghost Player":
            return True
        
        player_lookup = self._create_case_insensitive_lookup()
        return name.lower() in player_lookup
    
    def calculate_team_rating(self, player1: str, player2: str) -> float:
        """Calculate team rating as the average of individual ratings."""
        if not self.player_exists(player1):
             raise ValueError(f"Player not found: {player1}")
        if not self.player_exists(player2):
             raise ValueError(f"Player not found: {player2}")
            
        rating1 = self.get_ghost_player_rating() if player1.lower() == "ghost player" else self.players[player1]['rating']
        rating2 = self.get_ghost_player_rating() if player2.lower() == "ghost player" else self.players[player2]['rating']
        return (rating1 + rating2) / 2
        
    def get_k_factor(self, player: str) -> float:
        """
        Determine K-factor based on player experience.
        K-factor decreases as players play more tournaments.
        """
        tournaments_played = self.players[player]['tournaments_played']
        
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
            
        for player in all_players:
            if player not in self.players:
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
        
        # Process results and update ratings
        for position, (team, score) in self.resolve_tournament_positions(team_results):
            player1, player2 = team
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
                'team': list(team),  # Convert tuple to list for JSON
                'score': score,
                'position': position,
                'expected_position': expected_position,
                'team_rating': team_rating
            }
            tournament['results'].append(team_result)
            
            # Add team result to database if using DB
            if self.use_db:
                self.db_manager.add_team_result(
                    tournament_id, player1, player2, position, 
                    expected_position, score, team_rating
                )
            
            # Update individual ratings - skip ghost player
            for player in team:
                if player.lower() == "ghost player":
                    continue
                    
                k_factor = self.get_k_factor(player)
                old_rating = self.players[player]['rating']
                
                # Rating adjustment based on position difference
                # Normalize by number of teams to keep adjustments reasonable
                adjustment = k_factor * ((position_diff / len(teams)) + overall_modifier)
                new_rating = old_rating + adjustment
                
                # Update player data
                self.players[player]['rating'] = new_rating
                self.players[player]['tournaments_played'] += 1
                
                history_entry = {
                    'tournament_date': date,
                    'old_rating': old_rating,
                    'new_rating': new_rating,
                    'change': new_rating - old_rating,
                    'position': position,
                    'expected_position': expected_position,
                    'score': score,
                    'with_ghost': "Ghost Player" in team
                }
                
                self.players[player]['history'].append(history_entry)
                
                # Update player in database if using DB
                if self.use_db:
                    self.db_manager.update_player_rating(player, new_rating)
                    self.db_manager.increment_player_tournaments(player)
                    self.db_manager.add_player_history(
                        player, tournament_id, old_rating, new_rating,
                        position, expected_position, score, "Ghost Player" in team
                    )
                
        # Add tournament to history
        self.tournaments.append(tournament)
        print(f"Tournament recorded with {len(teams)} teams")
        
        # Save data
        self.save_data()
        
    def resolve_tournament_positions(self, results: Iterable[Tuple[Tuple[str, str], int]]) -> enumerate:
        pos = 1
        first = True
        previous_score: int
        standings = []
        for (team, score) in results:
            if first:
                first = False
                previous_score = score
            else:
                if previous_score != score: 
                    pos += 1
                    previous_score = score
            standings.append((pos,(team,score)))
        return standings

    
    def get_player_ratings(self) -> Dict[str, float]:
        """Return a dictionary of player names and their current ratings."""
        return {name: data['rating'] for name, data in self.players.items()}
        
    def get_player_details(self, player: str) -> Dict[str, Any]:
        """Get detailed information about a player."""
        if player not in self.players:
            raise ValueError(f"Player {player} not found")
            
        return self.players[player]
        
    def generate_balanced_teams(self, players: List[str], allow_ghost: bool = False) -> List[Tuple[str, str]]:
        """
        Generate balanced teams based on player ratings.
        
        Args:
            players: List of player names
            allow_ghost: If True, adds a ghost player when there's an odd number of players
            
        Returns:
            List of (player1, player2) tuples representing teams
        """
        if len(players) % 2 != 0:
            if not allow_ghost:
                raise ValueError("Need an even number of players")
                
            # Add a ghost player with average rating
            avg_rating = sum(self.players[p]['rating'] for p in players) / len(players)
            ghost_player = "Ghost Player"
            
            # Add ghost player to the system if not already present
            if ghost_player not in self.players:
                self.add_player(ghost_player, int(avg_rating))
            else:
                # Update ghost player rating to match current average
                self.players[ghost_player]['rating'] = int(avg_rating)
                
            print(f"Added ghost player with rating {int(avg_rating)} to balance teams")
            players.append(ghost_player)
            
        # Sort players by rating
        sorted_players = sorted(players, key=lambda p: self.players[p]['rating'], reverse=True)
        
        teams = []
        # Pair highest rated with lowest rated, second highest with second lowest, etc.
        for i in range(len(sorted_players) // 2):
            teams.append((sorted_players[i], sorted_players[-(i+1)]))
            
        return teams
        
    def predict_scores(self, teams: List[Tuple[str, str]], par: int = 64) -> Dict[Tuple[str, str], float]:
        """
        Predict scores for each team based on their ratings.
        
        Args:
            teams: List of (player1, player2) tuples representing teams
            par: Par score for the course
            
        Returns:
            Dictionary mapping teams to their predicted scores
        """
        # Calculate team ratings
        team_ratings = {}
        for team in teams:
            team_ratings[team] = self.calculate_team_rating(team[0], team[1])
            
        # Find the average rating
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
            if not hasattr(self, 'db_manager'):
                self.db_manager = TournamentDBManager(self.db_file)
                
            # Import data from JSON to database
            self.db_manager.import_from_json(self.json_file)
            print(f"Switched to database storage ({self.db_file})")
        else:
            # Export data from database to JSON
            if hasattr(self, 'db_manager'):
                self.db_manager.export_to_json(self.json_file)
            print(f"Switched to JSON storage ({self.json_file})")


def main():
    """Simple demonstration of the tournament rating system with database support."""
    # Initialize with JSON storage
    print("Initializing with JSON storage...")
    rating_system = TournamentRatingSystemDB(use_db=False)
    
    # Add some example players
    rating_system.add_player("Alice", 1100)
    rating_system.add_player("Bob", 1050)
    rating_system.add_player("Charlie", 950)
    rating_system.add_player("Dave", 900)
    rating_system.add_player("Eve", 1000)
    rating_system.add_player("Frank", 975)
    
    # Create teams
    teams = [
        ("Alice", "Dave"),
        ("Bob", "Charlie"),
        ("Eve", "Frank")
    ]
    
    # Predict tournament outcome
    predictions = rating_system.predict_tournament_outcome(teams)
    print("\nTournament Predictions:")
    for team, prediction in predictions.items():
        print(f"Team: {team[0]} & {team[1]}")
        print(f"  Rating: {prediction['rating']:.1f}")
        print(f"  Expected Position: {prediction['expected_position']:.1f}")
    
    # Record a tournament result
    # Teams are sorted by score (lowest first)
    team_results = [
        (("Bob", "Charlie"), 52),  # 1st place
        (("Alice", "Dave"), 54),   # 2nd place
        (("Eve", "Frank"), 58)     # 3rd place
    ]
    
    print("\nRecording tournament result in JSON storage...")
    rating_system.record_tournament(team_results, course_name="Pine Valley")
    
    # Show updated ratings
    print("\nUpdated Player Ratings:")
    for player, rating in rating_system.get_player_ratings().items():
        print(f"{player}: {rating:.1f}")
        
    # Switch to database storage
    print("\nSwitching to database storage...")
    rating_system.switch_storage_mode(use_db=True)
    
    # Record another tournament in database storage
    team_results = [
        (("Alice", "Dave"), 51),   # 1st place
        (("Eve", "Frank"), 53),    # 2nd place
        (("Bob", "Charlie"), 55)   # 3rd place
    ]
    
    print("\nRecording tournament result in database storage...")
    rating_system.record_tournament(team_results, course_name="Eagle Ridge")
    
    # Show updated ratings
    print("\nUpdated Player Ratings (from database):")
    for player, rating in rating_system.get_player_ratings().items():
        print(f"{player}: {rating:.1f}")


if __name__ == "__main__":
    main()
