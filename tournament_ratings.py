#!/usr/bin/env python3
"""
Tournament-Style Disc Golf League Rating System

This script implements a rating system for a doubles disc golf league where:
- All teams compete simultaneously on the course
- The winner is the team with the fewest total throws
- Ratings are adjusted based on expected vs. actual performance
"""

import json
import os
import datetime
import math
from typing import Dict, List, Tuple, Optional, Union, Any


class TournamentRatingSystem:
    def __init__(self, data_file: str = "tournament_data.json"):
        """Initialize the rating system with player data."""
        self.data_file = data_file
        self.players = {}  # Player name -> rating data
        self.tournaments = []  # List of past tournaments
        self.load_data()
        
    def load_data(self) -> None:
        """Load player and tournament data from file if it exists."""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                    self.players = data.get('players', {})
                    self.tournaments = data.get('tournaments', [])
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading data: {e}")
                # Initialize with empty data
                self.players = {}
                self.tournaments = []
        
    def save_data(self) -> None:
        """Save player and tournament data to file."""
        data = {
            'players': self.players,
            'tournaments': self.tournaments
        }
        try:
            with open(self.data_file, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"Data saved to {self.data_file}")
        except IOError as e:
            print(f"Error saving data: {e}")
    
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
        print(f"Added player {name} with initial rating {initial_rating}")
        
    def calculate_team_rating(self, player1: str, player2: str) -> float:
        """Calculate team rating as the average of individual ratings."""
        if player1 not in self.players or player2 not in self.players:
            raise ValueError(f"One or both players not found: {player1}, {player2}")
            
        rating1 = self.players[player1]['rating']
        rating2 = self.players[player2]['rating']
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
        total_rating = sum(team_ratings.values())
        team_predictions = {}
        
        for team, rating in team_ratings.items():
            # Higher rating means fewer expected throws
            # We invert the rating proportion to get expected position
            # (lower is better for position)
            relative_strength = rating / total_rating
            
            # Expected position (1-indexed, where 1 is best)
            # Lower expected_position means better expected performance
            expected_position = 1 + (1 - relative_strength) * (len(teams) - 1)
            
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
        
        # Process results and update ratings
        for position, (team, score) in enumerate(team_results, 1):
            player1, player2 = team
            team_rating = self.calculate_team_rating(player1, player2)
            expected_position = predictions[team]['expected_position']
            
            # Calculate performance rating
            # Performance is better when actual position is better than expected
            # (lower position number is better)
            position_diff = expected_position - position
            
            # Record team result
            team_result = {
                'team': list(team),  # Convert tuple to list for JSON
                'score': score,
                'position': position,
                'expected_position': expected_position,
                'team_rating': team_rating
            }
            tournament['results'].append(team_result)
            
            # Update individual ratings - skip ghost player
            for player in team:
                if player == "Ghost Player":
                    continue
                    
                k_factor = self.get_k_factor(player)
                old_rating = self.players[player]['rating']
                
                # Rating adjustment based on position difference
                # Normalize by number of teams to keep adjustments reasonable
                adjustment = k_factor * position_diff / len(teams)
                new_rating = old_rating + adjustment
                
                # Update player data
                self.players[player]['rating'] = new_rating
                self.players[player]['tournaments_played'] += 1
                self.players[player]['history'].append({
                    'tournament_date': date,
                    'old_rating': old_rating,
                    'new_rating': new_rating,
                    'change': new_rating - old_rating,
                    'position': position,
                    'expected_position': expected_position,
                    'score': score,
                    'with_ghost': "Ghost Player" in team
                })
                
        # Add tournament to history
        self.tournaments.append(tournament)
        print(f"Tournament recorded with {len(teams)} teams")
        
        # Save data
        self.save_data()
        
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
        
    def predict_scores(self, teams: List[Tuple[str, str]], par: int = 54) -> Dict[Tuple[str, str], float]:
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


def main():
    """Simple demonstration of the tournament rating system."""
    rating_system = TournamentRatingSystem()
    
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
    
    # Predict scores
    predicted_scores = rating_system.predict_scores(teams)
    print("\nPredicted Scores:")
    for team, score in predicted_scores.items():
        print(f"Team: {team[0]} & {team[1]} - {score:.1f}")
    
    # Record a tournament result
    # Teams are sorted by score (lowest first)
    team_results = [
        (("Bob", "Charlie"), 52),  # 1st place
        (("Alice", "Dave"), 54),   # 2nd place
        (("Eve", "Frank"), 58)     # 3rd place
    ]
    
    print("\nRecording tournament result...")
    rating_system.record_tournament(team_results, course_name="Pine Valley")
    
    # Show updated ratings
    print("\nUpdated Player Ratings:")
    for player, rating in rating_system.get_player_ratings().items():
        print(f"{player}: {rating:.1f}")


if __name__ == "__main__":
    main()
