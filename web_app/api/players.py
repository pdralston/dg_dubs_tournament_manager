"""
API endpoints for player management.
"""

from flask import Blueprint, jsonify, request, current_app

players_bp = Blueprint('players_api', __name__)


def _rs():
    return current_app.rating_system


@players_bp.route('/api/players', methods=['GET'])
def get_players():
    rs = _rs()
    players = [{'name': n, 'rating': d['rating'], 'tournaments_played': d['tournaments_played']}
               for n, d in rs.players.items()]
    players.sort(key=lambda x: x['rating'], reverse=True)
    return jsonify(players)


@players_bp.route('/api/players/<name>', methods=['GET'])
def get_player(name):
    rs = _rs()
    try:
        player_name = rs.get_player_name(name)
        player_data = rs.get_player(player_name)
        history = [{
            'date': e['tournament_date'], 'position': e['position'],
            'expected_position': e['expected_position'],
            'old_rating': e['old_rating'], 'new_rating': e['new_rating'],
            'change': e['change'], 'with_ghost': e['with_ghost'],
        } for e in player_data.get('history', [])]
        return jsonify({
            'name': player_name, 'rating': player_data['rating'],
            'tournaments_played': player_data['tournaments_played'], 'history': history,
        })
    except ValueError:
        return jsonify({'error': f"Player '{name}' not found"}), 404


@players_bp.route('/api/players', methods=['POST'])
def add_player():
    data = request.get_json()
    if not data or 'name' not in data:
        return jsonify({'error': 'Player name is required'}), 400
    name = data['name']
    rating = data.get('rating', 1000)
    try:
        _rs().add_player(name, rating)
        return jsonify({'name': name, 'rating': rating, 'tournaments_played': 0}), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
