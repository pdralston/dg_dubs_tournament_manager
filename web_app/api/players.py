"""
API endpoints for player management.
"""

from flask import Blueprint, jsonify, request
import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from tournament_core import TournamentRatingSystem

# Initialize blueprint
players_bp = Blueprint('players_api', __name__)

# Initialize rating system
rating_system = TournamentRatingSystem()

@players_bp.route('/api/players', methods=['GET'])
def get_players():
    """Get all players."""
    players = []
    for name, data in rating_system.players.items():
        players.append({
            'name': name,
            'rating': data['rating'],
            'tournaments_played': data['tournaments_played']
        })
    
    # Sort by rating (descending)
    players.sort(key=lambda x: x['rating'], reverse=True)
    
    return jsonify(players)

@players_bp.route('/api/players/<name>', methods=['GET'])
def get_player(name):
    """Get a specific player."""
    try:
        player_name = rating_system.get_player_name(name)  # Handle case-insensitive lookup
        player_data = rating_system.get_player(player_name)
        
        # Format history for response
        history = []
        for entry in player_data.get('history', []):
            history.append({
                'date': entry['tournament_date'],
                'position': entry['position'],
                'expected_position': entry['expected_position'],
                'old_rating': entry['old_rating'],
                'new_rating': entry['new_rating'],
                'change': entry['change'],
                'with_ghost': entry['with_ghost']
            })
        
        response = {
            'name': player_name,
            'rating': player_data['rating'],
            'tournaments_played': player_data['tournaments_played'],
            'history': history
        }
        
        return jsonify(response)
    except ValueError:
        return jsonify({'error': f"Player '{name}' not found"}), 404

@players_bp.route('/api/players', methods=['POST'])
def add_player():
    """Add a new player."""
    data = request.get_json()
    
    if not data or 'name' not in data:
        return jsonify({'error': 'Player name is required'}), 400
    
    name = data['name']
    rating = data.get('rating', 1000)
    
    try:
        rating_system.add_player(name, rating)
        return jsonify({
            'name': name,
            'rating': rating,
            'tournaments_played': 0,
            'message': f"Added player {name} with initial rating {rating}"
        }), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
