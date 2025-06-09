#!/usr/bin/env python3
"""
Tournament-Style Disc Golf League Manager

A command-line interface for managing the tournament-style disc golf league rating system
with flexible storage options (SQLite database or JSON).
"""

import os
import sys
import argparse
from typing import List, Tuple
from tournament_ratings import TournamentRatingSystem


class TournamentManager:
    def __init__(self, db_file: str = "tournament_data.db", use_db: bool = True):
        """
        Initialize the tournament manager.
        
        Args:
            db_file: Path to the SQLite database file
            use_db: Whether to use the database (True) or JSON (False)
        """
        self.rating_system = TournamentRatingSystem(db_file, use_db)
        
    def add_player(self, name: str, rating: int = 1000) -> None:
        """Add a new player to the system."""
        self.rating_system.add_player(name, rating)
        self.rating_system.save_data()

    def add_players_from_file(self, file: str) -> None:
        """
        Add multiple players from a file.
        
        The file should have one player per line in the format:
        PlayerName,SkillClass
        
        Where SkillClass is 'A' or 'B' ('A' players start with 1300 rating, 'B' with 1000)
        """
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
            print(f"File not found: {file}")
        except ValueError as e:
            print(f"Error: {e}")
            
    def list_players(self) -> None:
        """List all players and their ratings."""
        players = self.rating_system.players
        
        if not players:
            print("No players found.")
            return
            
        print("\nPlayer Ratings:")
        print("-" * 30)
        print(f"{'Player':<20} {'Rating':<10}")
        print("-" * 30)
        
        # Sort by rating (highest first)
        sorted_players = sorted(players.items(), key=lambda x: x[1]['rating'], reverse=True)
        
        for name, data in sorted_players:
            print(f"{name:<20} {data['rating']:<10.1f}")
            
    def record_tournament(self, results_file: str = None, course_name: str = None, date: str = None) -> None:
        """
        Record a tournament result.
        
        Args:
            results_file: Optional path to file containing results
            course_name: Optional name of the course
            date: Optional date string (defaults to today)
        """
        if results_file:
            self._record_tournament_from_file(results_file, course_name, date)
        else:
            self._record_tournament_interactive(course_name, date)
            
    def _record_tournament_from_file(self, results_file: str, course_name: str = None, date: str = None) -> None:
        """
        Record a tournament result from a file.
        
        Args:
            results_file: Path to file containing results
            course_name: Optional name of the course
            date: Optional date string (defaults to today)
        """
        team_results = []
        try:
            with open(results_file, 'r') as f:
                for line in f.readlines():
                    line = line.strip()
                    if not line:
                        continue
                    parts = line.split(",")
                    if len(parts) != 3:
                        print(f"Invalid line format: {line}")
                        continue
                    player1, player2, score = parts
                    team_results.append(((player1, player2), int(score)))
                    
            self.rating_system.record_tournament(team_results, course_name, date)
        except FileNotFoundError:
            print(f"File not found: {results_file}")
        except ValueError as e:
            print(f"Error: {e}")
            
    def _record_tournament_interactive(self, course_name: str = None, date: str = None) -> None:
        """
        Record a tournament result interactively.
        
        Args:
            course_name: Optional name of the course
            date: Optional date string (defaults to today)
        """
        if not course_name:
            course_name = input("Course name: ")
            
        if not date:
            date = input("Date (YYYY-MM-DD, leave blank for today): ")
            if not date:
                date = None
                
        print("\nEnter teams in order of finish (lowest score first).")
        print("Format: Player1,Player2,Score")
        print("Enter a blank line when done.")
        
        team_results = []
        i = 1
        while True:
            line = input(f"Team {i}: ")
            if not line:
                break
                
            parts = line.split(",")
            if len(parts) != 3:
                print("Invalid format. Please use: Player1,Player2,Score")
                continue
                
            player1, player2, score = parts
            try:
                team_results.append(((player1, player2), int(score)))
                i += 1
            except ValueError:
                print("Invalid score. Please enter a number.")
                
        if team_results:
            try:
                self.rating_system.record_tournament(team_results, course_name, date)
            except ValueError as e:
                print(f"Error: {e}")
                
    def predict_tournament(self, teams_file: str = None, par: int = 54) -> None:
        """
        Predict a tournament outcome from a file.
        
        Args:
            teams_file: Path to file containing teams
            par: Par score for the course
        """
        teams = []
        try:
            with open(teams_file, 'r') as f:
                lines = f.readlines()
                i = 0
                while i < len(lines):
                    player1 = lines[i].strip()
                    if not player1:
                        i += 1
                        continue
                        
                    if i + 1 < len(lines):
                        player2 = lines[i + 1].strip()
                        if not player2:
                            i += 2
                            continue
                    else:
                        player2 = "Ghost Player"
                        
                    teams.append((player1, player2))
                    i += 2
                    
            self._predict_tournament(teams, par)
        except FileNotFoundError:
            print(f"File not found: {teams_file}")
        except ValueError as e:
            print(f"Error: {e}")
            
    def predict_tournament_interactive(self, par: int = 54) -> None:
        """
        Predict a tournament outcome interactively.
        
        Args:
            par: Par score for the course
        """
        print("\nEnter teams, one player per line.")
        print("Enter a blank line when done.")
        
        teams = []
        while True:
            player1 = input("Player 1: ")
            if not player1:
                break
                
            player2 = input("Player 2 (leave blank for Ghost Player): ")
            if not player2:
                player2 = "Ghost Player"
                
            teams.append((player1, player2))
            print()
            
        if teams:
            try:
                self._predict_tournament(teams, par)
            except ValueError as e:
                print(f"Error: {e}")
                
    def _predict_tournament(self, teams: List[Tuple[str, str]], par: int = 54) -> None:
        """
        Predict a tournament outcome.
        
        Args:
            teams: List of (player1, player2) tuples
            par: Par score for the course
        """
        try:
            # Verify all players exist
            for team in teams:
                for player in team:
                    if not self.rating_system.player_exists(player) and player != "Ghost Player":
                        print(f"Error: Player '{player}' not found.")
                        return
                        
            # Get predictions
            predictions = self.rating_system.predict_tournament_outcome(teams)
            
            print("\nTournament Predictions:")
            print("-" * 80)
            print(f"{'Team':<50} {'Rating':<10} {'Expected Position':<20}")
            print("-" * 80)
            
            # Sort by expected position
            sorted_predictions = sorted(predictions.items(), key=lambda x: x[1]['expected_position'])
            
            for team, data in sorted_predictions:
                team_str = f"{team[0]} & {team[1]}"
                print(f"{team_str:<50} {data['rating']:<10.1f} {data['expected_position']:<20d}")
            
            print("\nCopyable Team List\n" + "-" * 17)
            [print(copy_string) for copy_string in [f"{team[0]}, {team[1]}" for team, score in sorted_predictions]]
                
            # Predict scores if par is provided
            if par:
                predicted_scores = self.rating_system.predict_scores(teams, par)
                
                print("\nPredicted Scores:")
                print("-" * 50)
                print(f"{'Team':<30} {'Score':<10}")
                print("-" * 50)
                
                # Sort by score (lowest first)
                sorted_scores = sorted(predicted_scores.items(), key=lambda x: x[1])
                
                for team, score in sorted_scores:
                    team_str = f"{team[0]} & {team[1]}"
                    print(f"{team_str:<30} {score:<10d}")
                    
        except ValueError as e:
            print(f"Error: {e}")
            
    def player_details_list(self, names: List[str]) -> None:
        for name in names: self.player_details(name)
    
    def player_details(self, name: str) -> None:
        """Show detailed information about a player."""
        try:
            details = self.rating_system.get_player_details(name)
            
            print(f"\nPlayer: {details['name']}")
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
                    change = entry['change']
                    change_str = f"{'+' if change >= 0 else ''}{change:.1f}"
                    print(f"{entry['tournament_date']:<12} {entry['position']:<10} {entry['expected_position']:<10.1f} "
                          f"{entry['old_rating']:<8.1f} {entry['new_rating']:<8.1f} {change_str:<8} "
                          f"{ghost_indicator}")
            else:
                print("\nNo rating history available.")
        except ValueError as e:
            print(f"Error: {e}")
            
    def generate_teams_from_file(self, file: str, allow_ghost: bool = False) -> None:
        """
        Generate balanced teams from a file containing player names.
        
        Args:
            file: Path to file containing player names (one per line)
            allow_ghost: Whether to allow a ghost player for odd numbers
        """
        player_list = []
        try:
            with open(file, 'r') as f:
                for line in f.readlines():
                    line = line.strip()
                    if not line:
                        continue
                    player_list.append(line)
        except FileNotFoundError:
            print(f"File not found: {file}")
            return
        except ValueError as e:
            print(f"Error: {e}")
            return
            
        self.generate_teams(players=player_list, allow_ghost=allow_ghost)
            
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
                if not self.rating_system.player_exists(player) and player != "Ghost Player":
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
        """Switch between database and JSON storage."""
        self.rating_system.switch_storage_mode(use_db)


def main():
    parser = argparse.ArgumentParser(description="Tournament-Style Disc Golf League Manager")
    parser.add_argument("--use-json", action="store_true", help="Use JSON storage instead of database")
    parser.add_argument("--db-file", default="tournament_data.db", help="Database file path")
    
    subparsers = parser.add_subparsers(dest="command")
    
    # Add player command
    add_parser = subparsers.add_parser("add", help="Add a player")
    add_parser.add_argument("name", nargs="?", help="Player name")
    add_parser.add_argument("--rating", type=int, default=1000, help="Initial rating")
    add_parser.add_argument("--file", help="File containing players to add")
    
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
    
    # List of players details command
    details_list_parser = subparsers.add_parser("details_list", help="Show the details for a list of players")
    details_list_parser.add_argument("names", nargs="+", help="Comma seperated list of player names")

    # Player details command
    details_parser = subparsers.add_parser("details", help="Show player details")
    details_parser.add_argument("name", help="Player name")
    
    # Generate teams command
    teams_parser = subparsers.add_parser("teams", help="Generate balanced teams")
    teams_group = teams_parser.add_mutually_exclusive_group(required=True)
    teams_group.add_argument("--players", nargs="+", help="List of player names")
    teams_group.add_argument("--file", help="File containing player names (one per line)")
    teams_parser.add_argument("--allow-ghost", action="store_true", help="Allow adding a ghost player for odd numbers")
    
    # Tournament history command
    history_parser = subparsers.add_parser("history", help="Show tournament history")
    history_parser.add_argument("--limit", type=int, help="Limit number of tournaments to show")
    
    # Storage command
    storage_parser = subparsers.add_parser("storage", help="Switch storage mode")
    storage_parser.add_argument("mode", choices=["db", "json"], help="Storage mode")
    
    args = parser.parse_args()
    
    # Create manager
    manager = TournamentManager(args.db_file, not args.use_json)
    
    # Process command
    if args.command == "add":
        if args.file:
            manager.add_players_from_file(args.file)
        elif args.name:
            manager.add_player(args.name, args.rating)
        else:
            print("Please specify a player name or file. Use --help for more information.")
    elif args.command == "list":
        manager.list_players()
    elif args.command == "record":
        manager.record_tournament(args.file, args.course, args.date)
    elif args.command == "predict":
        if args.file:
            manager.predict_tournament(args.file, args.par)
        else:
            manager.predict_tournament_interactive(args.par)
    elif args.command == "details":
        manager.player_details(args.name)
    elif args.command == "details_list":
        manager.player_details_list(args.names)
    elif args.command == "teams":
        if args.file:
            manager.generate_teams_from_file(args.file, args.allow_ghost)
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
