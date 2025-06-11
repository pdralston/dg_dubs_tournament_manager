"""
API endpoints for tournament management.
"""

from flask import Blueprint, jsonify, request
import datetime
import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from tournament_core import TournamentRatingSystem

# Initialize blueprint
tournaments_bp = Blueprint('tournaments_api', __name__)

# Initialize rating system
rating_system = TournamentRatingSystem()

@tournaments_bp.route('/api/tournaments', methods=['GET'])
def get_tournaments():
    """Get all tournaments."""
    tournaments = []
    for tournament in rating_system.tournaments:
        tournaments.append({
            'date': tournament['date'],
            'course': tournament['course'],
            'teams': tournament['teams'],
            'results': tournament['results']
        })
    
    # Sort by date (most recent first)
    tournaments.sort(key=lambda x: x['date'], reverse=True)
    
    return jsonify(tournaments)

@tournaments_bp.route('/api/tournaments', methods=['POST'])
def record_tournament():
    """Record a new tournament."""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    course = data.get('course', '')
    date = data.get('date', datetime.datetime.now().strftime("%Y-%m-%d"))
    team_results = data.get('team_results', [])
    
    if not team_results:
        return jsonify({'error': 'No team results provided'}), 400
    
    # Format team results
    formatted_results = []
    for team in team_results:
        if 'player1' in team and 'player2' in team and 'score' in team:
            try:
                score = int(team['score'])
                formatted_results.append(((team['player1'], team['player2']), score))
            except ValueError:
                return jsonify({'error': f"Invalid score for team {team['player1']} & {team['player2']}"}), 400
    
    if not formatted_results:
        return jsonify({'error': 'No valid team results provided'}), 400
    
    try:
        rating_system.record_tournament(formatted_results, course, date)
        return jsonify({
            'message': f"Tournament recorded with {len(formatted_results)} teams",
            'date': date,
            'course': course,
            'teams': len(formatted_results)
        }), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

@tournaments_bp.route('/api/predict', methods=['POST'])
def predict_tournament():
    """Predict tournament outcome."""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    teams = data.get('teams', [])
    par = data.get('par', 54)
    
    if not teams:
        return jsonify({'error': 'No teams provided'}), 400
    
    # Format teams
    formatted_teams = []
    for team in teams:
        if 'player1' in team and 'player2' in team:
            formatted_teams.append((team['player1'], team['player2']))
    
    if not formatted_teams:
        return jsonify({'error': 'No valid teams provided'}), 400
    
    try:
        predictions = rating_system.predict_tournament_outcome(formatted_teams)
        scores = rating_system.predict_scores(formatted_teams, par)
        
        # Format response
        results = []
        for team in formatted_teams:
            team_data = predictions[team]
            results.append({
                'player1': team[0],
                'player2': team[1],
                'team_rating': team_data.get('team_rating', 0),
                'expected_position': team_data.get('expected_position', 0),
                'predicted_score': scores[team]
            })
        
        # Sort by expected position
        results.sort(key=lambda x: x['expected_position'])
        
        return jsonify(results)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

@tournaments_bp.route('/api/teams', methods=['POST'])
def generate_teams():
    """Generate balanced teams."""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    players = data.get('players', [])
    allow_ghost = data.get('allow_ghost', False)
    
    if len(players) < 2:
        return jsonify({'error': 'At least 2 players are required'}), 400
    
    try:
        teams = rating_system.generate_balanced_teams(players, allow_ghost)
        predictions = rating_system.predict_tournament_outcome([tuple(team) for team in teams])
        
        # Format response
        results = []
        for team in teams:
            team_tuple = tuple(team)
            team_data = predictions[team_tuple]
            results.append({
                'player1': team[0],
                'player2': team[1],
                'team_rating': rating_system.calculate_team_rating(team[0], team[1]),
                'expected_position': team_data.get('expected_position', 0)
            })
        
        return jsonify(results)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
