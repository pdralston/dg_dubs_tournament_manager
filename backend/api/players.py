"""
API endpoints for player management.
"""

from flask import Blueprint, jsonify, request, current_app
from tournament_core.models import db, Player, PlayerHistory, Tournament, Season

players_bp = Blueprint('players_api', __name__)


def _rs():
    return current_app.rating_system


@players_bp.route('/api/players', methods=['GET'])
def get_players():
    rs = _rs()
    players = [{'name': n, 'rating': d['rating']} for n, d in rs.players.items()]
    players.sort(key=lambda x: x['rating'], reverse=True)
    return jsonify(players)


@players_bp.route('/api/players/<name>', methods=['GET'])
def get_player(name):
    rs = _rs()
    try:
        player_name = rs.get_player_name(name)
        player_data = rs.get_player(player_name)
        p = Player.query.filter_by(name=player_name).first()

        # Get available seasons
        seasons = [{'id': None, 'name': 'Current Season'}]
        for s in Season.query.order_by(Season.end_date.desc()).all():
            seasons.append({'id': s.season_id, 'name': s.season_name})

        # Build history grouped by season
        season_filter = request.args.get('season_id')

        if season_filter and season_filter != 'null':
            # Archived season
            sid = int(season_filter)
            history_entries = PlayerHistory.query.filter_by(player_id=p.player_id).join(
                Tournament, PlayerHistory.tournament_id == Tournament.tournament_id
            ).filter(Tournament.season_id == sid).order_by(Tournament.date.desc()).all()
        else:
            # Current season — tournaments with no season_id
            history_entries = PlayerHistory.query.filter_by(player_id=p.player_id).join(
                Tournament, PlayerHistory.tournament_id == Tournament.tournament_id
            ).filter(Tournament.season_id.is_(None)).order_by(Tournament.date.desc()).all()

        history = [{
            'date': h.tournament.date.isoformat(), 'position': h.position,
            'expected_position': float(h.expected_position), 'old_rating': float(h.old_rating),
            'new_rating': float(h.new_rating), 'change': float(h.new_rating - h.old_rating),
            'with_ghost': h.with_ghost, 'tournament_id': h.tournament_id,
        } for h in history_entries]

        lifetime_tournaments = PlayerHistory.query.filter_by(player_id=p.player_id).count() if p else 0

        return jsonify({
            'name': player_name, 'rating': player_data['rating'],
            'tournaments_played': lifetime_tournaments,
            'seasonal_cash': float(p.seasonal_cash) if p else 0,
            'lifetime_cash': float(p.lifetime_cash) + (float(p.seasonal_cash) if p else 0) if p else 0,
            'seasons': seasons,
            'history': history,
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
