"""
API endpoints for tournament management.
"""

from flask import Blueprint, jsonify, request, current_app
import datetime

tournaments_bp = Blueprint('tournaments_api', __name__)


def _rs():
    return current_app.rating_system


@tournaments_bp.route('/api/tournaments', methods=['GET'])
def get_tournaments():
    rs = _rs()
    tournaments = [{'date': t['date'], 'course': t['course'], 'teams': t['teams'], 'results': t['results']}
                   for t in rs.tournaments]
    tournaments.sort(key=lambda x: x['date'], reverse=True)
    return jsonify(tournaments)


@tournaments_bp.route('/api/tournaments', methods=['POST'])
def record_tournament():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    course = data.get('course', '')
    date = data.get('date', datetime.datetime.now().strftime("%Y-%m-%d"))
    team_results = data.get('team_results', [])
    if not team_results:
        return jsonify({'error': 'No team results provided'}), 400

    formatted = []
    for t in team_results:
        if 'player1' in t and 'player2' in t and 'score' in t:
            try:
                formatted.append(((t['player1'], t['player2']), int(t['score'])))
            except ValueError:
                return jsonify({'error': f"Invalid score for team {t['player1']} & {t['player2']}"}), 400
    if not formatted:
        return jsonify({'error': 'No valid team results provided'}), 400

    try:
        _rs().record_tournament(formatted, course, date)
        return jsonify({'message': f"Tournament recorded with {len(formatted)} teams", 'date': date, 'course': course}), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@tournaments_bp.route('/api/predict', methods=['POST'])
def predict_tournament():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    teams = data.get('teams', [])
    par = data.get('par', 54)
    if not teams:
        return jsonify({'error': 'No teams provided'}), 400

    formatted = [(t['player1'], t['player2']) for t in teams if 'player1' in t and 'player2' in t]
    if not formatted:
        return jsonify({'error': 'No valid teams provided'}), 400

    rs = _rs()
    try:
        predictions = rs.predict_tournament_outcome(formatted)
        scores = rs.predict_scores(formatted, par)
        results = [{
            'player1': t[0], 'player2': t[1],
            'team_rating': predictions[t].get('rating', 0),
            'expected_position': predictions[t].get('expected_position', 0),
            'predicted_score': scores[t],
        } for t in formatted]
        results.sort(key=lambda x: x['expected_position'])
        return jsonify(results)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@tournaments_bp.route('/api/teams', methods=['POST'])
def generate_teams():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    players = data.get('players', [])
    allow_ghost = data.get('allow_ghost', False)
    if len(players) < 2:
        return jsonify({'error': 'At least 2 players are required'}), 400

    rs = _rs()
    try:
        teams = rs.generate_balanced_teams(players, allow_ghost)
        predictions = rs.predict_tournament_outcome([tuple(t) for t in teams])
        results = [{
            'player1': t[0], 'player2': t[1],
            'team_rating': rs.calculate_team_rating(t[0], t[1]),
            'expected_position': predictions[tuple(t)].get('expected_position', 0),
        } for t in teams]
        return jsonify(results)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
