#!/usr/bin/env python3
"""
Tournament Manager CLI

This script provides a command-line interface for the tournament rating system.
"""

import argparse
import sys
import os
import sys
# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tournament_core import TournamentRatingSystem

def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(description='Disc Golf League Tournament Rating System')
    parser.add_argument('--use-json', action='store_true', help='Use JSON storage instead of database')
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Add player command
    add_parser = subparsers.add_parser('add', help='Add a player')
    add_parser.add_argument('name', nargs='?', help='Player name')
    add_parser.add_argument('--rating', type=float, default=1000, help='Initial rating')
    add_parser.add_argument('--file', help='CSV file with player names and skill classes')
    
    # List players command
    subparsers.add_parser('list', help='List all players')
    
    # Player details command
    details_parser = subparsers.add_parser('details', help='Show player details')
    details_parser.add_argument('name', help='Player name')
    
    # Record tournament command
    record_parser = subparsers.add_parser('record', help='Record tournament results')
    record_parser.add_argument('--file', help='File with team results')
    record_parser.add_argument('--course', help='Course name')
    record_parser.add_argument('--date', help='Tournament date (YYYY-MM-DD)')
    
    # Predict tournament command
    predict_parser = subparsers.add_parser('predict', help='Predict tournament outcome')
    predict_parser.add_argument('--file', help='File with teams')
    predict_parser.add_argument('--par', type=int, default=54, help='Par score for the course')
    
    # Generate teams command
    teams_parser = subparsers.add_parser('teams', help='Generate balanced teams')
    teams_parser.add_argument('--players', nargs='+', help='List of players')
    teams_parser.add_argument('--allow-ghost', action='store_true', help='Allow ghost player for odd number of players')
    
    # Tournament history command
    history_parser = subparsers.add_parser('history', help='Show tournament history')
    history_parser.add_argument('--limit', type=int, help='Limit number of tournaments to show')
    
    # Storage command
    storage_parser = subparsers.add_parser('storage', help='Change storage mode')
    storage_parser.add_argument('mode', choices=['db', 'json'], help='Storage mode')
    
    args = parser.parse_args()
    
    # Initialize rating system with appropriate storage
    rating_system = TournamentRatingSystem(use_db=not args.use_json)
    
    # Execute command
    if args.command == 'add':
        if args.file:
            # Add players from file
            try:
                with open(args.file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                            
                        parts = line.split(',')
                        if len(parts) >= 2:
                            name = parts[0].strip()
                            skill_class = parts[1].strip().upper()
                            
                            # Set rating based on skill class
                            if skill_class == 'A':
                                rating = 1300
                            else:
                                rating = 1000
                                
                            try:
                                rating_system.add_player(name, rating)
                                print(f"Added player {name} with initial rating {rating}")
                            except ValueError as e:
                                print(f"Error adding player {name}: {e}")
                        else:
                            print(f"Invalid line in player file: {line}")
            except FileNotFoundError:
                print(f"File not found: {args.file}")
                sys.exit(1)
        elif args.name:
            # Add single player
            try:
                rating_system.add_player(args.name, args.rating)
                print(f"Added player {args.name} with initial rating {args.rating}")
            except ValueError as e:
                print(f"Error: {e}")
                sys.exit(1)
        else:
            print("Error: Player name or file required")
            sys.exit(1)
            
    elif args.command == 'list':
        # List all players
        players = []
        for name, data in rating_system.players.items():
            players.append((name, data['rating'], data['tournaments_played']))
            
        # Sort by rating (descending)
        players.sort(key=lambda x: x[1], reverse=True)
        
        if players:
            print("\nPlayer Ratings:")
            print("-" * 30)
            print(f"{'Player':<20} {'Rating':<10}")
            print("-" * 30)
            for name, rating, _ in players:
                print(f"{name:<20} {rating:<10}")
        else:
            print("No players found.")
            
    elif args.command == 'details':
        # Show player details
        try:
            player_name = rating_system.get_player_name(args.name)
            player_data = rating_system.get_player(player_name)
            
            print(f"\nPlayer: {player_name}")
            print("-" * 40)
            print(f"Current Rating: {player_data['rating']}")
            print(f"Tournaments Played: {player_data['tournaments_played']}")
            
            if player_data['history']:
                print("\nRating History:")
                print(f"{'Date':<12} {'Position':<10} {'Expected':<10} {'Old':<8} {'New':<8} {'Change':<8} {'Ghost?':<8}")
                print("-" * 70)
                
                for entry in player_data['history']:
                    change = entry['new_rating'] - entry['old_rating']
                    change_str = f"+{change}" if change > 0 else str(change)
                    ghost = "Yes" if entry['with_ghost'] else "No"
                    
                    print(f"{entry['tournament_date']:<12} {entry['position']:<10} {entry['expected_position']:<10.1f} "
                          f"{entry['old_rating']:<8.1f} {entry['new_rating']:<8.1f} {change_str:<8} {ghost:<8}")
            else:
                print("\nNo tournament history available.")
                
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)
            
    elif args.command == 'record':
        # Record tournament results
        if args.file:
            # Read teams from file
            try:
                team_results = []
                with open(args.file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                            
                        parts = line.split(',')
                        if len(parts) >= 3:
                            player1 = parts[0].strip()
                            player2 = parts[1].strip()
                            score = int(parts[2].strip())
                            
                            team_results.append(((player1, player2), score))
                        else:
                            print(f"Invalid line in results file: {line}")
                            
                if not team_results:
                    print("No valid team results found in file.")
                    sys.exit(1)
                    
                try:
                    rating_system.record_tournament(team_results, args.course, args.date)
                    print(f"Tournament recorded with {len(team_results)} teams")
                except ValueError as e:
                    print(f"Error: {e}")
                    sys.exit(1)
                    
            except FileNotFoundError:
                print(f"File not found: {args.file}")
                sys.exit(1)
        else:
            # Interactive mode
            print("Enter team results (one team per line, format: Player1,Player2,Score):")
            print("Enter a blank line when done.")
            
            team_results = []
            while True:
                line = input("> ")
                if not line:
                    break
                    
                parts = line.split(',')
                if len(parts) >= 3:
                    player1 = parts[0].strip()
                    player2 = parts[1].strip()
                    try:
                        score = int(parts[2].strip())
                        team_results.append(((player1, player2), score))
                    except ValueError:
                        print(f"Invalid score: {parts[2]}")
                else:
                    print("Invalid format. Use: Player1,Player2,Score")
                    
            if not team_results:
                print("No team results entered.")
                sys.exit(1)
                
            try:
                rating_system.record_tournament(team_results, args.course, args.date)
                print(f"Tournament recorded with {len(team_results)} teams")
            except ValueError as e:
                print(f"Error: {e}")
                sys.exit(1)
                
    elif args.command == 'predict':
        # Predict tournament outcome
        if args.file:
            # Read teams from file
            try:
                teams = []
                with open(args.file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                            
                        parts = line.split(',')
                        if len(parts) >= 2:
                            player1 = parts[0].strip()
                            player2 = parts[1].strip()
                            
                            teams.append((player1, player2))
                        else:
                            print(f"Invalid line in teams file: {line}")
                            
                if not teams:
                    print("No valid teams found in file.")
                    sys.exit(1)
                    
            except FileNotFoundError:
                print(f"File not found: {args.file}")
                sys.exit(1)
        else:
            # Interactive mode
            print("Enter teams (one team per line, format: Player1,Player2):")
            print("Enter a blank line when done.")
            
            teams = []
            while True:
                line = input("> ")
                if not line:
                    break
                    
                parts = line.split(',')
                if len(parts) >= 2:
                    player1 = parts[0].strip()
                    player2 = parts[1].strip()
                    teams.append((player1, player2))
                else:
                    print("Invalid format. Use: Player1,Player2")
                    
            if not teams:
                print("No teams entered.")
                sys.exit(1)
                
        try:
            # Get predictions
            predictions = rating_system.predict_tournament_outcome(teams)
            scores = rating_system.predict_scores(teams, args.par)
            
            # Sort by expected position
            sorted_teams = sorted(predictions.items(), key=lambda x: x[1]['expected_position'])
            
            print("\nTournament Predictions:")
            print("-" * 60)
            print(f"{'Team':<30} {'Rating':<10} {'Expected Position':<20}")
            print("-" * 60)
            
            for team, data in sorted_teams:
                team_str = f"{team[0]} & {team[1]}"
                team_rating = data.get('team_rating', 0)
                expected_position = data.get('expected_position', 0)
                print(f"{team_str:<30} {team_rating:<10.1f} {expected_position:<20.1f}")
                
            print("\nPredicted Scores:")
            print("-" * 50)
            print(f"{'Team':<30} {'Score':<10}")
            print("-" * 50)
            
            for team, score in sorted(scores.items(), key=lambda x: x[1]):
                team_str = f"{team[0]} & {team[1]}"
                print(f"{team_str:<30} {score:<10.1f}")
                
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)
            
    elif args.command == 'teams':
        # Generate balanced teams
        if args.players:
            players = args.players
        else:
            # Interactive mode
            print("Enter player names (one per line):")
            print("Enter a blank line when done.")
            
            players = []
            while True:
                line = input("> ")
                if not line:
                    break
                players.append(line.strip())
                
            if not players:
                print("No players entered.")
                sys.exit(1)
                
        try:
            teams = rating_system.generate_balanced_teams(players, args.allow_ghost)
            predictions = rating_system.predict_tournament_outcome([tuple(team) for team in teams])
            scores = rating_system.predict_scores([tuple(team) for team in teams], 54)  # Assume par 54
            
            print("\nGenerated Teams:")
            print("-" * 50)
            for i, team in enumerate(teams):
                team_rating = rating_system.calculate_team_rating(team[0], team[1])
                print(f"Team {i+1}: {team[0]} & {team[1]} (Rating: {team_rating})")
                
            print("\nTournament Predictions:")
            print("-" * 60)
            print(f"{'Team':<30} {'Rating':<10} {'Expected Position':<20}")
            print("-" * 60)
            
            for team in teams:
                team_tuple = tuple(team)
                team_str = f"{team[0]} & {team[1]}"
                data = predictions[team_tuple]
                team_rating = data.get('team_rating', 0)
                expected_position = data.get('expected_position', 0)
                print(f"{team_str:<30} {team_rating:<10.1f} {expected_position:<20.1f}")
                
            print("\nPredicted Scores:")
            print("-" * 50)
            print(f"{'Team':<30} {'Score':<10}")
            print("-" * 50)
            
            for team in teams:
                team_tuple = tuple(team)
                team_str = f"{team[0]} & {team[1]}"
                score = scores[team_tuple]
                print(f"{team_str:<30} {score:<10.1f}")
                
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)
            
    elif args.command == 'history':
        # Show tournament history
        tournaments = rating_system.tournaments
        
        if args.limit and args.limit > 0:
            tournaments = tournaments[:args.limit]
            
        if not tournaments:
            print("No tournament history available.")
            sys.exit(0)
            
        for i, tournament in enumerate(tournaments):
            print(f"\nTournament {i+1} - {tournament['date']}")
            if tournament.get('course'):
                print(f"Course: {tournament['course']}")
            print(f"Teams: {tournament['teams']}")
            print("-" * 50)
            print(f"{'Position':<10} {'Team':<30} {'Score':<10}")
            print("-" * 50)
            
            for result in tournament['results']:
                team_str = f"{result['team'][0]} & {result['team'][1]}"
                print(f"{result['position']:<10} {team_str:<30} {result['score']:<10}")
                
    elif args.command == 'storage':
        # Change storage mode
        if args.mode == 'db':
            rating_system.switch_storage_mode(True)
            print("Switched to database storage (tournament_data.db)")
        else:
            rating_system.switch_storage_mode(False)
            print("Switched to JSON storage (tournament_data.json)")
            
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
