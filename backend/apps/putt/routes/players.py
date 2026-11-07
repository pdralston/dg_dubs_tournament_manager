"""DG-Putt player registry endpoints."""

import csv
import io

from flask import Blueprint, jsonify, request

from backend.models import (
    db,
    PuttPlayer as RegisteredPlayer,
    PuttRegistration as TournamentRegistration,
    PuttTournament as Tournament,
    PuttTeam as Team,
    PuttTeamHistory as TeamHistory,  # noqa: F401
    PuttSeason as Season,
)
from backend.shared.auth import require_role
from .matches import _is_team_undefeated

players_bp = Blueprint('putt_players', __name__, url_prefix='/api/putt')


@players_bp.route('/players/<int:player_id>', methods=['GET'])
def get_player_detail(player_id):
    player = RegisteredPlayer.query.get(player_id)
    if not player:
        return jsonify({'error': 'Player not found'}), 404

    # Get tournament history
    tournaments = db.session.query(Tournament, TournamentRegistration, Team).join(
        TournamentRegistration, Tournament.tournament_id == TournamentRegistration.tournament_id
    ).outerjoin(
        Team, db.and_(Team.tournament_id == Tournament.tournament_id,
                      db.or_(Team.player1_id == player_id, Team.player2_id == player_id))
    ).filter(TournamentRegistration.player_id == player_id).all()

    # Get teammate history with names
    teammates = db.session.query(TeamHistory, RegisteredPlayer).join(
        RegisteredPlayer, TeamHistory.teammate_id == RegisteredPlayer.player_id
    ).filter(TeamHistory.player_id == player_id).all()

    # Get tournament history with ace-pot-win check. An ace-pot win = the
    # player's team finished 1st AND went undefeated. Uses the shared
    # _is_team_undefeated helper so this matches the archive's definition
    # exactly (single source of truth).
    tournaments_with_undefeated = []
    for t in tournaments:
        tournament_obj, registration, team = t
        won_ace_pot = (
            team is not None
            and team.final_place == 1
            and _is_team_undefeated(tournament_obj.tournament_id, team.team_id)
        )
        tournaments_with_undefeated.append((tournament_obj, registration, team, won_ace_pot))

    # Live current-season figures (current season = tournaments not yet archived,
    # i.e. season_id IS NULL). These are not stored on the player row until a
    # season archive runs, so we compute them on the fly here.
    season_wins_current = sum(
        1 for (t_obj, _reg, team, _won) in tournaments_with_undefeated
        if t_obj.season_id is None and team and team.final_place == 1
    )
    ace_pots_current = sum(
        1 for (t_obj, _reg, _team, won) in tournaments_with_undefeated
        if t_obj.season_id is None and won
    )

    # Stored values are cumulative across archived seasons; add the live current
    # season to present an up-to-date lifetime figure.
    lifetime_wins = (player.seasonal_wins or 0) + season_wins_current
    lifetime_ace_pots = (player.lifetime_ace_pots or 0) + ace_pots_current

    return jsonify({
        'player_id': player.player_id,
        'player_name': player.player_name,
        'nickname': player.nickname,
        'division': player.division,
        'seasonal_points': player.seasonal_points,
        'seasonal_cash': float(player.seasonal_cash),
        'lifetime_earnings': float(player.lifetime_earnings or 0),
        'lifetime_ace_pots': lifetime_ace_pots,
        'events_participated': player.events_participated or 0,
        'seasonal_wins': season_wins_current,
        'lifetime_wins': lifetime_wins,
        'average_place': float(player.average_place) if player.average_place else None,
        'tournament_history': [{
            'tournament_id': t[0].tournament_id,
            'tournament_date': t[0].tournament_date.isoformat(),
            'status': t[0].status,
            'bought_ace_pot': t[1].bought_ace_pot,
            'final_place': t[2].final_place if t[2] else None,
            'points_earned': t[2].points_earned if t[2] else 0,
            'won_ace_pot': t[3],
            'season_name': Season.query.get(t[0].season_id).season_name if t[0].season_id else None
        } for t in tournaments_with_undefeated],
        'teammate_history': [{
            'teammate_id': th[0].teammate_id,
            'teammate_name': th[1].player_name,
            'teammate_nickname': th[1].nickname,
            'times_paired': th[0].times_paired,
            'average_place': float(th[0].average_place) if th[0].average_place else None
        } for th in teammates]
    })


@players_bp.route('/players', methods=['GET'])
def get_players():
    players = RegisteredPlayer.query.all()
    return jsonify([{
        'player_id': p.player_id,
        'player_name': p.player_name,
        'nickname': p.nickname,
        'division': p.division,
        'seasonal_points': p.seasonal_points,
        'seasonal_cash': float(p.seasonal_cash)
    } for p in players])


@players_bp.route('/players', methods=['POST'])
@require_role(app='putt', role='director')
def create_players():
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    players_data = data if isinstance(data, list) else [data]
    created_players = []
    errors = []

    for player_data in players_data:
        if not player_data.get('player_name'):
            errors.append('Player name is required')
            continue

        division = player_data.get('division', 'Am')
        if division not in ['Pro', 'Am', 'Junior']:
            errors.append('Division must be Pro, Am, or Junior')
            continue

        existing = RegisteredPlayer.query.filter_by(player_name=player_data['player_name']).first()
        if existing:
            errors.append(f'"{player_data["player_name"]}" already exists')
            continue

        player = RegisteredPlayer(
            player_name=player_data['player_name'],
            nickname=player_data.get('nickname'),
            division=division,
            seasonal_points=0,
            seasonal_cash=0.00
        )

        db.session.add(player)
        created_players.append(player)

    if errors and not created_players:
        return jsonify({'errors': errors}), 400

    db.session.commit()

    result = {
        'created': [{
            'player_id': p.player_id,
            'player_name': p.player_name,
            'nickname': p.nickname,
            'division': p.division,
            'seasonal_points': p.seasonal_points,
            'seasonal_cash': float(p.seasonal_cash)
        } for p in created_players]
    }

    if errors:
        result['errors'] = errors

    return jsonify(result), 201


@players_bp.route('/players/<int:player_id>', methods=['PUT'])
@require_role(app='putt', role='director')
def update_player(player_id):
    player = RegisteredPlayer.query.get(player_id)
    if not player:
        return jsonify({'error': 'Player not found'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    if 'player_name' in data:
        player.player_name = data['player_name']
    if 'nickname' in data:
        player.nickname = data['nickname']
    if 'division' in data:
        player.division = data['division']

    try:
        db.session.commit()
        return jsonify({
            'player_id': player.player_id,
            'player_name': player.player_name,
            'nickname': player.nickname,
            'division': player.division,
            'seasonal_points': player.seasonal_points,
            'seasonal_cash': float(player.seasonal_cash)
        })
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Failed to update player'}), 500


@players_bp.route('/players/batch-csv', methods=['POST'])
@require_role(app='putt', role='director')
def create_players_csv():
    if not request.json or 'csv_data' not in request.json:
        return jsonify({'error': 'csv_data field required'}), 400

    csv_data = request.json['csv_data']
    reader = csv.DictReader(io.StringIO(csv_data))

    players_data = []
    for row in reader:
        # Handle case-insensitive column lookup
        division = row.get('division', row.get('Division', 'Am')).strip()
        # Normalize division case
        if division.lower() == 'pro':
            division = 'Pro'
        elif division.lower() == 'junior':
            division = 'Junior'
        else:
            division = 'Am'

        players_data.append({
            'player_name': row.get('player_name', '').strip(),
            'nickname': row.get('nickname', '').strip() or None,
            'division': division
        })

    created_players = []
    errors = []

    for i, player_data in enumerate(players_data):
        if not player_data.get('player_name'):
            errors.append(f'Row {i + 1}: Player name is required')
            continue

        division = player_data.get('division', 'Am')
        if division not in ['Pro', 'Am', 'Junior']:
            errors.append(f'Row {i + 1}: Division must be Pro, Am, or Junior')
            continue

        existing = RegisteredPlayer.query.filter_by(player_name=player_data['player_name']).first()
        if existing:
            errors.append(f'Row {i + 1}: Player name "{player_data["player_name"]}" already exists')
            continue

        player = RegisteredPlayer(
            player_name=player_data['player_name'],
            nickname=player_data.get('nickname'),
            division=division,
            seasonal_points=0,
            seasonal_cash=0.00
        )

        db.session.add(player)
        created_players.append(player)

    if errors and not created_players:
        return jsonify({'errors': errors}), 400

    db.session.commit()

    result = {
        'created': [{
            'player_id': p.player_id,
            'player_name': p.player_name,
            'nickname': p.nickname,
            'division': p.division
        } for p in created_players]
    }

    if errors:
        result['errors'] = errors

    return jsonify(result), 201
