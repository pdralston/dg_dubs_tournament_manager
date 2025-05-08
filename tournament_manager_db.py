#!/usr/bin/env python3
"""
Tournament-Style Disc Golf League Manager with Database Support

A command-line interface for managing the tournament-style disc golf league rating system
with optional SQLite database support.
"""

import os
import sys
import argparse
from typing import List, Tuple
from tournament_ratings_db import TournamentRatingSystemDB


class TournamentManagerDB:
    def __init__(self, db_file: str = "tournament_data.db", use_db: bool = True):
        """
        Initialize the tournament manager.
        
        Args:
            db_file: Path to the SQLite database file
            use_db: Whether to use the database (True) or JSON (False)
        """
        self.rating_system = TournamentRatingSystemDB(db_file, use_db)
        
    def add_player(self, name: str, rating: int = 1000) -> None:
        """Add a new player to the system."""
        self.rating_system.add_player(name, rating)
        self.rating_system.save_data()

    def add_players(self, file: str) -> None:
        try:
            with open(file, 'r') as f:
                for line in f.readlines():
                    line = line.strip()
                    if not line:
                        continue
                    parts = line.split(",")
                    if len(parts) != 2:
                        continue
                    self.rating_system.add_player(parts[0], 1300 if parts[1].lower() == 'a' else 1000)
            self.rating_system.save_data()
        except FileNotFoundError:
            print(f"File not found: {results_file}")
        except ValueError as e:
            print(f"Error: {e}")
        
    def list_players(self) -> None:
        """List all players and their ratings."""
        players = self.rating_system.get_player_ratings()
        if not players:
            print("No players in the system.")
            return
            
        print("\nPlayer Ratings:")
        print("-" * 30)
        print(f"{'Player':<20} {'Rating':<10}")
        print("-" * 30)
        
        # Sort by rating
        sorted_players = sorted(players.items(), key=lambda x: x[1], reverse=True)
        for name, rating in sorted_players:
            print(f"{name:<20} {rating:<10.1f}")
            
    def record_tournament(self, results_file: str, course_name: str = None, date: str = None) -> None:
        """
        Record a tournament result from a file.
        
        The file should have one team per line in the format:
        Player1,Player2,Score
        
        Teams should be listed in order of finish (lowest score first).
        """
        try:
            with open(results_file, 'r') as f:
                lines = f.readlines()
                
            team_results = []
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                parts = line.split(',')
                if len(parts) != 3:
                    print(f"Invalid line format: {line}")
                    print("Expected format: Player1,Player2,Score")
                    return
                    
                player1 = parts[0].strip()
                player2 = parts[1].strip()
                try:
                    score = int(parts[2].strip())
                except ValueError:
                    print(f"Invalid score: {parts[2]}")
                    return
                    
                team_results.append(((player1, player2), score))
                
            # Sort by score (lowest first) if not already sorted
            team_results.sort(key=lambda x: x[1])
            
            self.rating_system.record_tournament(team_results, course_name, date)
            
        except FileNotFoundError:
            print(f"File not found: {results_file}")
        except ValueError as e:
            print(f"Error: {e}")
            
    def record_tournament_interactive(self, course_name: str = None, date: str = None) -> None:
        """Record a tournament result interactively."""
        print("\nEnter tournament results (lowest score first).")
        print("For each team, enter: Player1,Player2,Score")
        print("Enter a blank line when done.")
        
        team_results = []
        position = 1
        
        while True:
            line = input(f"Team {position}: ").strip()
            if not line:
                break
                
            parts = line.split(',')
            if len(parts) != 3:
                print("Invalid format. Expected: Player1,Player2,Score")
                continue
                
            player1 = parts[0].strip()
            player2 = parts[1].strip()
            
            try:
                score = int(parts[2].strip())
            except ValueError:
                print(f"Invalid score: {parts[2]}")
                continue
                
            team_results.append(((player1, player2), score))
            position += 1
            
        if not team_results:
            print("No results entered.")
            return
            
        try:
            self.rating_system.record_tournament(team_results, course_name, date)
        except ValueError as e:
            print(f"Error: {e}")
            
    def predict_tournament(self, teams_file: str, par: int = None) -> None:
        """
        Predict tournament outcome from a file listing teams.
        
        The file should have one team per line in the format:
        Player1,Player2
        """
        try:
            with open(teams_file, 'r') as f:
                lines = f.readlines()
                
            teams = []
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                parts = line.split(',')
                if len(parts) != 2:
                    print(f"Invalid line format: {line}")
                    print("Expected format: Player1,Player2")
                    return
                    
                player1 = parts[0].strip()
                player2 = parts[1].strip()
                teams.append((player1, player2))
                
            self._predict_tournament(teams, par)
            
        except FileNotFoundError:
            print(f"File not found: {teams_file}")
        except ValueError as e:
            print(f"Error: {e}")
            
    def predict_tournament_interactive(self, par: int = None) -> None:
        """Predict tournament outcome interactively."""
        print("\nEnter teams for tournament prediction.")
        print("For each team, enter: Player1,Player2")
        print("Enter a blank line when done.")
        
        teams = []
        team_num = 1
        
        while True:
            line = input(f"Team {team_num}: ").strip()
            if not line:
                break
                
            parts = line.split(',')
            if len(parts) != 2:
                print("Invalid format. Expected: Player1,Player2")
                continue
                
            player1 = parts[0].strip()
            player2 = parts[1].strip()
            teams.append((player1, player2))
            team_num += 1
            
        if not teams:
            print("No teams entered.")
            return
            
        self._predict_tournament(teams, par)
            
    def _predict_tournament(self, teams: List[Tuple[str, str]], par: int = None) -> None:
        """Internal method to predict tournament outcome."""
        try:
            # Verify all players exist
            all_players = set()
            for p1, p2 in teams:
                all_players.add(p1)
                all_players.add(p2)
                
            for player in all_players:
                if player not in self.rating_system.players:
                    print(f"Warning: Player '{player}' not found in the system.")
                    return
            
            # Get predictions
            predictions = self.rating_system.predict_tournament_outcome(teams)
            
            print("\nTournament Predictions:")
            print("-" * 80)
            print(f"{'Team':<50} {'Rating':<10} {'Expected Position':<20}")
            print("-" * 80)
            
            # Sort by expected position
            sorted_predictions = sorted(predictions.items(), key=lambda x: x[1]['expected_position'])
            
            for team, prediction in sorted_predictions:
                team_str = f"{team[0]} & {team[1]}"
                print(f"{team_str:<50} {prediction['rating']:<10.1f} {prediction['expected_position']:^20d}")
                
            # If par is provided, predict scores
            if par is not None:
                predicted_scores = self.rating_system.predict_scores(teams, par)
                
                print("\nPredicted Scores:")
                print("-" * 50)
                print(f"{'Team':<30} {'Predicted Score':<15}")
                print("-" * 50)
                
                # Sort by predicted score
                sorted_scores = sorted(predicted_scores.items(), key=lambda x: x[1])
                
                for team, score in sorted_scores:
                    team_str = f"{team[0]} & {team[1]}"
                    print(f"{team_str:<30} {score:<15.1f}")
                    
        except ValueError as e:
            print(f"Error: {e}")
            
    def player_details(self, name: str) -> None:
        """Show detailed information about a player."""
        try:
            details = self.rating_system.get_player_details(name)
            
            print(f"\nPlayer: {name}")
            print("-" * 40)
            print(f"Current Rating: {details['rating']:.1f}")
            print(f"Tournaments Played: {details['tournaments_played']}")
            
            if details['history']:
                print("\nRating History:")
                print(f"{'Date':<12} {'Position':<10} {'Expected':<10} {'Old':<8} {'New':<8} {'Change':<8} {'Ghost?':<8}")
                print("-" * 70)
                
                # Sort by date (newest first)
                sorted_history = sorted(details['history'], key=lambda x: x['tournament_date'], reverse=True)
                
                for entry in sorted_history:
                    ghost_indicator = "Yes" if entry.get('with_ghost', False) else "No"
                    print(f"{entry['tournament_date']:<12} {entry['position']:<10} {entry['expected_position']:<10.1f} "
                          f"{entry['old_rating']:<8.1f} {entry['new_rating']:<8.1f} {entry['change']:+.1f} {ghost_indicator:<8}")
            else:
                print("\nNo rating history available.")
                
        except ValueError as e:
            print(f"Error: {e}")
            
    def generate_teams_from_file(self, file: str) -> None:
        player_list = []
        try:
            with open(file, 'r') as f:
                for line in f.readlines():
                    line = line.strip()
                    if not line:
                        continue
                    player_list.append(line)
        except FileNotFoundError:
            print(f"File not found: {results_file}")
        except ValueError as e:
            print(f"Error: {e}")
        finally:
            self.generate_teams(players=player_list, allow_ghost=True)

    def generate_teams(self, players: List[str], allow_ghost: bool = False) -> None:
        """
        Generate balanced teams from a list of players.
        
        Args:
            players: List of player names
            allow_ghost: If True, adds a ghost player when there's an odd number of players
        """
        if len(players) % 2 != 0 and not allow_ghost:
            print("Error: Need an even number of players. Use --allow-ghost to add a ghost player.")
            return
            
        try:
            # Verify all players exist
            for player in players:
                if player not in self.rating_system.players and player != "Ghost Player":
                    print(f"Error: Player '{player}' not found.")
                    return
                    
            teams = self.rating_system.generate_balanced_teams(players, allow_ghost)
            
            print("\nGenerated Teams:")
            print("-" * 50)
            
            for i, (p1, p2) in enumerate(teams, 1):
                team_rating = self.rating_system.calculate_team_rating(p1, p2)
                print(f"Team {i}: {p1} & {p2} (Rating: {team_rating:.1f})")
                
            # Predict tournament outcome
            self._predict_tournament(teams)
                
        except ValueError as e:
            print(f"Error: {e}")
            
    def tournament_history(self, limit: int = None) -> None:
        """Show tournament history."""
        tournaments = self.rating_system.tournaments
        
        if not tournaments:
            print("No tournaments recorded.")
            return
            
        if limit is not None:
            tournaments = tournaments[-limit:]
            
        for i, tournament in enumerate(reversed(tournaments), 1):
            print(f"\nTournament {i} - {tournament['date']}")
            if tournament.get('course'):
                print(f"Course: {tournament['course']}")
            print(f"Teams: {tournament['teams']}")
            print("-" * 60)
            print(f"{'Position':<10} {'Team':<40} {'Score':^10}")
            print("-" * 60)
            
            for result in tournament['results']:
                team_str = f"{result['team'][0]} & {result['team'][1]}"
                print(f"{result['position']:<10} {team_str:<40} {result['score']:^10}")
                
    def switch_storage(self, use_db: bool) -> None:
        """
        Switch between database and JSON storage.
        
        Args:
            use_db: True to use database, False to use JSON
        """
        self.rating_system.switch_storage_mode(use_db)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Tournament-Style Disc Golf League Manager with Database Support")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Add player command
    add_parser = subparsers.add_parser("add", help="Add a new player")
    add_parser.add_argument("--name", default="", help="Player name")
    add_parser.add_argument("--file", help="File containing players and their skill class (A/B)")
    add_parser.add_argument("--rating", type=int, default=1000, help="Initial rating (default: 1000)")
    
    # List players command
    subparsers.add_parser("list", help="List all players and their ratings")
    
    # Record tournament command
    record_parser = subparsers.add_parser("record", help="Record a tournament result")
    record_parser.add_argument("--file", help="File containing tournament results")
    record_parser.add_argument("--course", help="Course name")
    record_parser.add_argument("--date", help="Tournament date (YYYY-MM-DD)")
    
    # Predict tournament command
    predict_parser = subparsers.add_parser("predict", help="Predict tournament outcome")
    predict_parser.add_argument("--file", help="File containing teams")
    predict_parser.add_argument("--par", type=int, help="Par score for the course")
    
    # Player details command
    details_parser = subparsers.add_parser("details", help="Show player details")
    details_parser.add_argument("name", help="Player name")
    
    # Generate teams command
    teams_parser = subparsers.add_parser("teams", help="Generate balanced teams")
    teams_parser.add_argument("--players", nargs="+", help="List of player names")
    teams_parser.add_argument("--file", help="File with each player on a seperate line")
    teams_parser.add_argument("--allow-ghost", action="store_true", help="Allow adding a ghost player for odd numbers")
    
    # Tournament history command
    history_parser = subparsers.add_parser("history", help="Show tournament history")
    history_parser.add_argument("--limit", type=int, help="Limit number of tournaments to show")
    
    # Storage command
    storage_parser = subparsers.add_parser("storage", help="Switch storage mode")
    storage_parser.add_argument("mode", choices=["json", "db"], help="Storage mode to use")
    
    # Global options
    parser.add_argument("--use-db", action="store_true", help="Use SQLite database for storage")
    parser.add_argument("--db-file", default="tournament_data.db", help="SQLite database file path")
    
    return parser.parse_args()


def main():
    """Main entry point for the tournament manager."""
    args = parse_args()
    
    # Initialize manager with specified storage mode
    manager = TournamentManagerDB(
        db_file=args.db_file if hasattr(args, 'db_file') else "tournament_data.db",
        use_db=args.use_db if hasattr(args, 'use_db') else False
    )
    
    if args.command == "add":
        if args.file:
            manager.add_players(args.file)
        else:
            manager.add_player(args.name, args.rating)
    elif args.command == "list":
        manager.list_players()
    elif args.command == "record":
        if args.file:
            manager.record_tournament(args.file, args.course, args.date)
        else:
            manager.record_tournament_interactive(args.course, args.date)
    elif args.command == "predict":
        if args.file:
            manager.predict_tournament(args.file, args.par)
        else:
            manager.predict_tournament_interactive(args.par)
    elif args.command == "details":
        manager.player_details(args.name)
    elif args.command == "teams":
        if args.file:
            manager.generate_teams_from_file(args.file)
        else:
            manager.generate_teams(args.players, args.allow_ghost)
    elif args.command == "history":
        manager.tournament_history(args.limit)
    elif args.command == "storage":
        manager.switch_storage(args.mode == "db")
    else:
        print("Please specify a command. Use --help for more information.")


if __name__ == "__main__":
    main()
