"""DG-Putt in-progress tournament editing endpoints."""

from flask import Blueprint, request, jsonify

from backend.models import (
    db,
    PuttTournament as Tournament,
    PuttMatch as Match,
    PuttTeam as Team,
    PuttRegistration as TournamentRegistration,
    PuttPlayer as RegisteredPlayer,
)
from backend.shared.auth import require_role

tournament_edit_bp = Blueprint('putt_tournament_edit', __name__, url_prefix='/api/putt')


@tournament_edit_bp.route('/tournaments/<int:tournament_id>/edit/match/<int:match_id>/teams', methods=['PUT'])
@require_role(app='putt', role='director')
def update_match_teams(tournament_id, match_id):
    """Update team assignments for a match"""
    data = request.get_json()

    match = Match.query.filter_by(tournament_id=tournament_id, match_id=match_id).first()
    if not match:
        return jsonify({'error': 'Match not found'}), 404

    # Validate teams exist in tournament
    if data.get('team1_id'):
        team1 = Team.query.filter_by(team_id=data['team1_id'], tournament_id=tournament_id).first()
        if not team1:
            return jsonify({'error': 'Team 1 not found in tournament'}), 400

    if data.get('team2_id'):
        team2 = Team.query.filter_by(team_id=data['team2_id'], tournament_id=tournament_id).first()
        if not team2:
            return jsonify({'error': 'Team 2 not found in tournament'}), 400

    match.team1_id = data.get('team1_id')
    match.team2_id = data.get('team2_id')

    db.session.commit()
    return jsonify({'message': 'Match teams updated successfully'})


@tournament_edit_bp.route('/tournaments/<int:tournament_id>/edit/matches', methods=['POST'])
@require_role(app='putt', role='director')
def add_match(tournament_id):
    """Add a new match to tournament"""
    data = request.get_json()

    tournament = Tournament.query.get(tournament_id)
    if not tournament:
        return jsonify({'error': 'Tournament not found'}), 404

    # Get next match_id
    max_match = db.session.query(db.func.max(Match.match_id)).filter_by(tournament_id=tournament_id).scalar()
    next_match_id = (max_match or 0) + 1

    match = Match(
        tournament_id=tournament_id,
        match_id=next_match_id,
        stage_type=data['stage_type'],
        round_type=data['round_type'],
        round_number=data['round_number'],
        position_in_round=data['position_in_round'],
        stage_match_number=data['stage_match_number'],
        match_order=data['match_order'],
        team1_id=data.get('team1_id'),
        team2_id=data.get('team2_id'),
        station_assignment=data.get('station_assignment'),
        winner_advances_to_match_id=data.get('winner_advances_to_match_id'),
        loser_advances_to_match_id=data.get('loser_advances_to_match_id')
    )

    db.session.add(match)
    db.session.commit()

    return jsonify({'message': 'Match added successfully', 'match_id': next_match_id})


@tournament_edit_bp.route('/tournaments/<int:tournament_id>/edit/match/<int:match_id>/progression', methods=['PUT'])
@require_role(app='putt', role='director')
def update_match_progression(tournament_id, match_id):
    """Update match progression targets"""
    data = request.get_json()

    match = Match.query.filter_by(tournament_id=tournament_id, match_id=match_id).first()
    if not match:
        return jsonify({'error': 'Match not found'}), 404

    # Validate target matches exist
    if data.get('winner_advances_to_match_id'):
        target = Match.query.filter_by(
            tournament_id=tournament_id,
            match_id=data['winner_advances_to_match_id']
        ).first()
        if not target:
            return jsonify({'error': 'Winner target match not found'}), 400

    if data.get('loser_advances_to_match_id'):
        target = Match.query.filter_by(
            tournament_id=tournament_id,
            match_id=data['loser_advances_to_match_id']
        ).first()
        if not target:
            return jsonify({'error': 'Loser target match not found'}), 400

    match.winner_advances_to_match_id = data.get('winner_advances_to_match_id')
    match.loser_advances_to_match_id = data.get('loser_advances_to_match_id')

    db.session.commit()
    return jsonify({'message': 'Match progression updated successfully'})


@tournament_edit_bp.route('/tournaments/<int:tournament_id>/edit/replace-player', methods=['PUT'])
@require_role(app='putt', role='director')
def replace_player(tournament_id):
    """Replace a player in tournament registration and all associated teams"""
    data = request.get_json()
    old_player_id = data.get('old_player_id')
    new_player_id = data.get('new_player_id')

    if not old_player_id or not new_player_id:
        return jsonify({'error': 'Both old_player_id and new_player_id required'}), 400

    tournament = Tournament.query.get(tournament_id)
    if not tournament:
        return jsonify({'error': 'Tournament not found'}), 404

    # Verify old player is registered
    old_registration = TournamentRegistration.query.filter_by(
        tournament_id=tournament_id,
        player_id=old_player_id
    ).first()
    if not old_registration:
        return jsonify({'error': 'Old player not registered in tournament'}), 404

    # Verify new player exists
    new_player = RegisteredPlayer.query.get(new_player_id)
    if not new_player:
        return jsonify({'error': 'New player not found'}), 404

    # Check if new player already registered
    existing_registration = TournamentRegistration.query.filter_by(
        tournament_id=tournament_id,
        player_id=new_player_id
    ).first()
    if existing_registration:
        return jsonify({'error': 'New player already registered in tournament'}), 400

    # Update registration
    old_registration.player_id = new_player_id

    # Update all teams where old player appears
    teams = Team.query.filter_by(tournament_id=tournament_id).all()
    updated_teams = 0
    for team in teams:
        if team.player1_id == old_player_id:
            team.player1_id = new_player_id
            updated_teams += 1
        elif team.player2_id == old_player_id:
            team.player2_id = new_player_id
            updated_teams += 1

    db.session.commit()
    return jsonify({
        'message': 'Player replaced successfully',
        'teams_updated': updated_teams
    })
