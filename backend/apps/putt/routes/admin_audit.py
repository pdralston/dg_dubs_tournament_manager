"""DG-Putt admin audit: manual final-place override + dependent-stat recalc."""

from flask import Blueprint, jsonify, request

from backend.models import (
    db,
    PuttTournament as Tournament,
    PuttTeam as Team,
    PuttMatch as Match,
    PuttPlayer as RegisteredPlayer,
    PuttTeamHistory as TeamHistory,
)
from backend.shared.auth import require_role

admin_audit_bp = Blueprint('putt_admin_audit', __name__, url_prefix='/api/putt')


@admin_audit_bp.route('/admin/tournaments/<int:tournament_id>/audit', methods=['GET'])
@require_role(app='putt', role='admin')
def get_tournament_audit_data(tournament_id):
    """Get complete tournament data for auditing"""
    tournament = Tournament.query.get(tournament_id)
    if not tournament:
        return jsonify({'error': 'Tournament not found'}), 404

    # Get all teams with player info
    teams = Team.query.filter_by(tournament_id=tournament_id).all()

    teams_data = []
    for team in teams:
        player1 = RegisteredPlayer.query.get(team.player1_id)
        player2 = RegisteredPlayer.query.get(team.player2_id) if team.player2_id else None

        teams_data.append({
            'team_id': team.team_id,
            'player1_id': team.player1_id,
            'player1_name': player1.player_name if player1 else 'Unknown',
            'player2_id': team.player2_id,
            'player2_name': player2.player_name if player2 else None,
            'is_ghost_team': team.is_ghost_team,
            'final_place': team.final_place,
            'points_earned': team.points_earned
        })

    # Get all matches
    matches = Match.query.filter_by(tournament_id=tournament_id).order_by(Match.match_order).all()
    match_data = []
    for match in matches:
        match_data.append({
            'match_id': match.match_id,
            'stage_type': match.stage_type,
            'round_type': match.round_type,
            'round_number': match.round_number,
            'team1_id': match.team1_id,
            'team2_id': match.team2_id,
            'team1_score': match.team1_score,
            'team2_score': match.team2_score,
            'match_status': match.match_status
        })

    return jsonify({
        'tournament': {
            'tournament_id': tournament.tournament_id,
            'tournament_date': tournament.tournament_date.isoformat(),
            'status': tournament.status,
            'ace_pot_payout': float(tournament.ace_pot_payout)
        },
        'teams': teams_data,
        'matches': match_data
    })


@admin_audit_bp.route('/admin/tournaments/<int:tournament_id>/recalculate', methods=['POST'])
@require_role(app='putt', role='admin')
def recalculate_tournament_stats(tournament_id):
    """Recalculate tournament-derived stats based on current final places (preserve manual overrides)"""
    tournament = Tournament.query.get(tournament_id)
    if not tournament or tournament.status != 'Completed':
        return jsonify({'error': 'Tournament not found or not completed'}), 404

    try:
        # Reset only the derived data, preserve final places
        _reset_derived_data_preserve_places(tournament_id)

        # Recalculate based on current final places (manual or original)
        from .matches import (
            _update_teammate_history, _update_seasonal_points, _distribute_cash_payouts,
        )

        _update_teammate_history(tournament_id)
        _update_seasonal_points(tournament_id)
        _distribute_cash_payouts(tournament_id)

        db.session.commit()
        return jsonify({'message': 'Tournament stats recalculated successfully'})

    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Failed to recalculate tournament stats'}), 500


@admin_audit_bp.route('/admin/tournaments/<int:tournament_id>/teams/<int:team_id>/place', methods=['PUT'])
@require_role(app='putt', role='admin')
def update_team_place(tournament_id, team_id):
    """Manually update a team's final place"""
    data = request.get_json()
    new_place = data.get('final_place')

    if not isinstance(new_place, int) or new_place < 1:
        return jsonify({'error': 'Invalid place value'}), 400

    team = Team.query.filter_by(tournament_id=tournament_id, team_id=team_id).first()
    if not team:
        return jsonify({'error': 'Team not found'}), 404

    old_place = team.final_place
    team.final_place = new_place

    try:
        db.session.commit()
        # Force session refresh to ensure changes are visible
        db.session.refresh(team)

        return jsonify({
            'team_id': team_id,
            'old_place': old_place,
            'new_place': new_place,
            'message': 'Team place updated. Run recalculate to update dependent stats.'
        })
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Failed to update team place'}), 500


def _reset_derived_data_preserve_places(tournament_id):
    """Reset derived data but preserve manually set final places"""
    teams = Team.query.filter_by(tournament_id=tournament_id).all()

    # Store old values for proper rollback
    team_old_data = {}
    for team in teams:
        team_old_data[team.team_id] = {
            'final_place': team.final_place,
            'points_earned': team.points_earned or 0
        }

    # Reset only points, preserve final_place
    for team in teams:
        old_points = team.points_earned or 0
        team.points_earned = 0  # Will be recalculated
        # DON'T reset final_place - preserve manual overrides

        # Subtract old points from players
        if team.player1_id:
            player1 = RegisteredPlayer.query.get(team.player1_id)
            if player1:
                player1.seasonal_points = max(0, player1.seasonal_points - old_points)

        if team.player2_id:
            player2 = RegisteredPlayer.query.get(team.player2_id)
            if player2:
                player2.seasonal_points = max(0, player2.seasonal_points - old_points)

    # Reset teammate history for this tournament's teams
    for team in teams:
        if team.player2_id and not team.is_ghost_team:
            old_final_place = team_old_data[team.team_id]['final_place']
            if old_final_place:  # Only process if there was a previous final place
                for player_id, teammate_id in [(team.player1_id, team.player2_id), (team.player2_id, team.player1_id)]:
                    history = TeamHistory.query.filter_by(player_id=player_id, teammate_id=teammate_id).first()
                    if history and history.times_paired > 0:
                        # Recalculate average without this tournament
                        if history.times_paired == 1:
                            db.session.delete(history)
                        else:
                            total_place = (history.average_place * history.times_paired) - old_final_place
                            history.times_paired -= 1
                            history.average_place = total_place / history.times_paired if history.times_paired > 0 else 0
