"""DG-Putt tournament lifecycle endpoints."""

import random
from datetime import datetime
from decimal import Decimal

from flask import Blueprint, jsonify, request

from backend.models import (
    db,
    PuttTournament as Tournament,
    PuttRegistration as TournamentRegistration,
    PuttPlayer as RegisteredPlayer,
    PuttAcePot as AcePot,
    PuttTeam as Team,
    PuttMatch as Match,
    PuttTeamHistory as TeamHistory,
    PuttSeason as Season,
)
from backend.shared.auth import require_role

tournaments_bp = Blueprint('putt_tournaments', __name__, url_prefix='/api/putt')


def safe_float(val):
    return float(val) if val is not None else 0.0


def _register_players_helper(tournament_id, tournament_date, players_data, ace_pot_per_player=1.00):
    """Helper function to register players and handle ace pot"""
    registered_players = []
    ace_pot_buyins = 0

    for player_data in players_data:
        if isinstance(player_data, dict):
            player_id = player_data.get('player_id')
            bought_ace_pot = player_data.get('bought_ace_pot', False)
        else:
            player_id = player_data
            bought_ace_pot = False

        player = RegisteredPlayer.query.get(player_id)
        if not player:
            raise ValueError(f'Player ID {player_id} not found')

        # Check if already registered
        existing_reg = TournamentRegistration.query.filter_by(
            tournament_id=tournament_id,
            player_id=player_id
        ).first()

        if not existing_reg:
            registration = TournamentRegistration(
                tournament_id=tournament_id,
                player_id=player_id,
                bought_ace_pot=bought_ace_pot
            )
            db.session.add(registration)
            registered_players.append(player)

            if bought_ace_pot:
                ace_pot_buyins += 1

    # Add ace pot entry if there are buy-ins
    if ace_pot_buyins > 0:
        ace_pot_amount = ace_pot_buyins * float(ace_pot_per_player)
        ace_pot_entry = AcePot(
            tournament_id=tournament_id,
            date=tournament_date,
            description=f'Tournament {tournament_date}: {ace_pot_buyins} buy-ins',
            amount=ace_pot_amount
        )
        db.session.add(ace_pot_entry)

    return registered_players, ace_pot_buyins


@tournaments_bp.route('/tournaments', methods=['GET'])
def get_tournaments():
    date_param = request.args.get('date')
    id_param = request.args.get('id')

    if date_param or id_param:
        if date_param:
            try:
                tournament_date = datetime.strptime(date_param, '%Y-%m-%d').date()
                tournament = Tournament.query.filter_by(tournament_date=tournament_date).first()
            except ValueError:
                return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        else:
            try:
                tournament_id = int(id_param)
                if tournament_id <= 0:
                    return jsonify({'error': 'Invalid tournament ID'}), 400
                tournament = Tournament.query.get(tournament_id)
            except (ValueError, TypeError):
                return jsonify({'error': 'Invalid tournament ID'}), 400

        if not tournament:
            return jsonify({'error': 'Tournament not found'}), 404

        registrations = db.session.query(TournamentRegistration, RegisteredPlayer).join(
            RegisteredPlayer, TournamentRegistration.player_id == RegisteredPlayer.player_id
        ).filter(TournamentRegistration.tournament_id == tournament.tournament_id).all()

        teams = Team.query.filter_by(tournament_id=tournament.tournament_id).all()

        return jsonify({
            'tournament_id': tournament.tournament_id,
            'tournament_date': tournament.tournament_date.isoformat(),
            'status': tournament.status,
            'total_teams': tournament.total_teams,
            'ace_pot_payout': safe_float(tournament.ace_pot_payout),
            'first_payout': safe_float(tournament.first_payout),
            'second_payout': safe_float(tournament.second_payout),
            'registered_players': [{
                'player_id': reg[1].player_id,
                'player_name': reg[1].player_name,
                'nickname': reg[1].nickname,
                'division': reg[1].division,
                'bought_ace_pot': reg[0].bought_ace_pot
            } for reg in registrations],
            'teams': [{
                'team_id': t.team_id,
                'player1_id': t.player1_id,
                'player2_id': t.player2_id,
                'is_ghost_team': t.is_ghost_team,
                'seed_number': t.seed_number,
                'points_earned': t.points_earned
            } for t in teams]
        })
    else:
        # Optional season filter. When omitted (or 'current'), return the current
        # (not-yet-archived) season whose tournaments have season_id IS NULL.
        season_param = request.args.get('season_id')
        try:
            query = Tournament.query
            if season_param and season_param != 'current':
                try:
                    season_id = int(season_param)
                    if season_id <= 0:
                        return jsonify({'error': 'Invalid season ID'}), 400
                except (ValueError, TypeError):
                    return jsonify({'error': 'Invalid season ID'}), 400
                query = query.filter_by(season_id=season_id)
            else:
                query = query.filter_by(season_id=None)

            tournaments = query.order_by(Tournament.tournament_id.desc()).all()
            return jsonify([{
                'tournament_id': t.tournament_id,
                'tournament_date': t.tournament_date.isoformat() if t.tournament_date else None,
                'status': t.status,
                'total_teams': t.total_teams,
                'ace_pot_payout': float(t.ace_pot_payout) if t.ace_pot_payout else 0.00
            } for t in tournaments])
        except Exception:
            return jsonify({'error': 'Failed to fetch tournaments'}), 500


@tournaments_bp.route('/seasons', methods=['GET'])
def get_seasons():
    """List archived seasons, most recent first, for the season selector."""
    try:
        seasons = Season.query.order_by(Season.end_date.desc(), Season.season_id.desc()).all()
        return jsonify([{
            'season_id': s.season_id,
            'season_name': s.season_name,
            'start_date': s.start_date.isoformat() if s.start_date else None,
            'end_date': s.end_date.isoformat() if s.end_date else None,
            'archived_at': s.archived_at.isoformat() if s.archived_at else None
        } for s in seasons])
    except Exception:
        return jsonify({'error': 'Failed to fetch seasons'}), 500


@tournaments_bp.route('/tournaments', methods=['POST'])
@require_role(app='putt', role='director')
def create_tournament():
    data = request.get_json()

    if not data or not data.get('tournament_date'):
        return jsonify({'error': 'Tournament date is required'}), 400

    try:
        tournament_date = datetime.strptime(data['tournament_date'], '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

    players = data.get('players', [])
    if len(players) < 2:
        return jsonify({'error': 'At least 2 players required to create tournament'}), 400

    stations = data.get('stations', 6)
    if not isinstance(stations, int) or stations < 1 or stations > 20:
        return jsonify({'error': 'Stations must be between 1 and 20'}), 400

    try:
        ace_pot_per_player = float(data.get('ace_pot_per_player', data.get('ace_pot_per_player')))
        if ace_pot_per_player < 0:
            return jsonify({'error': 'Ace pot amount cannot be negative'}), 400
    except (TypeError, ValueError):
        return jsonify({'error': 'Invalid ace pot amount'}), 400

    try:
        buy_in_per_player = float(data.get('buy_in_per_player', 5.00))
        if buy_in_per_player < 0:
            return jsonify({'error': 'Buy-in amount cannot be negative'}), 400
    except (TypeError, ValueError):
        return jsonify({'error': 'Invalid buy-in amount'}), 400

    payout_config = data.get('payout_config', None)
    if payout_config is not None:
        if not isinstance(payout_config, dict) or payout_config.get('mode') not in ('percentage', 'fixed'):
            return jsonify({'error': 'Invalid payout_config'}), 400

    try:
        # Create tournament
        tournament = Tournament(
            tournament_date=tournament_date,
            status='Scheduled',
            total_teams=0,
            ace_pot_payout=0.00,
            stations=stations,
            buy_in_per_player=buy_in_per_player,
            payout_config=payout_config
        )

        db.session.add(tournament)
        db.session.flush()  # Get tournament ID

        # Register players using helper
        registered_players, ace_pot_buyins = _register_players_helper(
            tournament.tournament_id, tournament_date, players, ace_pot_per_player
        )

        # Generate teams
        player_list = registered_players.copy()
        teams = []

        while len(player_list) >= 2:
            player_one = player_list.pop()
            n = len(player_list)
            index = random.randint(0, n - 1)

            if index >= n:
                player_two = player_list.pop()
            else:
                player_two = player_list[index]
                player_list[index] = player_list[n - 1]
                player_list.pop()

            team = Team(
                tournament_id=tournament.tournament_id,
                player1_id=player_one.player_id,
                player2_id=player_two.player_id,
                is_ghost_team=False,
                seed_number=len(teams) + 1
            )
            db.session.add(team)
            teams.append(team)

        # Handle odd player (ghost team)
        if len(player_list) > 0:
            team = Team(
                tournament_id=tournament.tournament_id,
                player1_id=player_list.pop().player_id,
                player2_id=None,
                is_ghost_team=True,
                seed_number=len(teams) + 1
            )
            db.session.add(team)
            teams.append(team)

        tournament.total_teams = len(teams)
        db.session.commit()

        return jsonify({
            'tournament_id': tournament.tournament_id,
            'tournament_date': tournament.tournament_date.isoformat(),
            'status': tournament.status,
            'total_teams': tournament.total_teams,
            'total_players': len(registered_players),
            'teams_generated': len(teams),
            'ace_pot_buyins': ace_pot_buyins,
            'ace_pot_amount': ace_pot_buyins * ace_pot_per_player
        }), 201

    except ValueError as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Failed to create tournament'}), 500


@tournaments_bp.route('/tournaments/pending', methods=['POST'])
@require_role(app='putt', role='director')
def create_pending_tournament():
    data = request.get_json()
    if not data or not data.get('tournament_date'):
        return jsonify({'error': 'Tournament date is required'}), 400
    try:
        tournament_date = datetime.strptime(data['tournament_date'], '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

    stations = data.get('stations', 6)
    if not isinstance(stations, int) or stations < 1 or stations > 20:
        return jsonify({'error': 'Stations must be between 1 and 20'}), 400

    try:
        buy_in_per_player = float(data.get('buy_in_per_player', 5.00))
        ace_pot_per_player = float(data.get('ace_pot_per_player', 1.00))  # noqa: F841
    except (TypeError, ValueError):
        return jsonify({'error': 'Invalid numeric value'}), 400

    payout_config = data.get('payout_config', None)

    tournament = Tournament(
        tournament_date=tournament_date,
        status='Pending',
        total_teams=0,
        ace_pot_payout=0.00,
        stations=stations,
        buy_in_per_player=buy_in_per_player,
        payout_config=payout_config
    )
    db.session.add(tournament)
    db.session.commit()
    return jsonify({
        'tournament_id': tournament.tournament_id,
        'status': tournament.status
    }), 201


@tournaments_bp.route('/tournaments/<int:tournament_id>/finalize', methods=['POST'])
@require_role(app='putt', role='director')
def finalize_tournament(tournament_id):
    tournament = Tournament.query.get(tournament_id)
    if not tournament:
        return jsonify({'error': 'Tournament not found'}), 404
    if tournament.status != 'Pending':
        return jsonify({'error': 'Tournament is not in Pending state'}), 400

    data = request.get_json() or {}
    ace_pot_per_player = float(data.get('ace_pot_per_player', 1.00))  # noqa: F841

    registrations = TournamentRegistration.query.filter_by(tournament_id=tournament_id).all()
    if len(registrations) < 2:
        return jsonify({'error': 'At least 2 players required'}), 400

    try:
        player_list = [RegisteredPlayer.query.get(r.player_id) for r in registrations]
        player_list = [p for p in player_list if p]
        teams = []

        while len(player_list) >= 2:
            player_one = player_list.pop()
            n = len(player_list)
            index = random.randint(0, n - 1)
            player_two = player_list[index]
            player_list[index] = player_list[n - 1]
            player_list.pop()

            team = Team(
                tournament_id=tournament_id,
                player1_id=player_one.player_id,
                player2_id=player_two.player_id,
                is_ghost_team=False,
                seed_number=len(teams) + 1
            )
            db.session.add(team)
            teams.append(team)

        if player_list:
            team = Team(
                tournament_id=tournament_id,
                player1_id=player_list.pop().player_id,
                player2_id=None,
                is_ghost_team=True,
                seed_number=len(teams) + 1
            )
            db.session.add(team)
            teams.append(team)

        tournament.total_teams = len(teams)
        tournament.status = 'Scheduled'
        db.session.commit()

        return jsonify({
            'tournament_id': tournament_id,
            'status': tournament.status,
            'total_teams': tournament.total_teams
        })
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Failed to finalize tournament'}), 500


@tournaments_bp.route('/tournaments/<int:tournament_id>/players', methods=['POST'])
@require_role(app='putt', role='director')
def add_player_to_pending(tournament_id):
    """Add a single player to a Pending tournament and update ace pot if applicable."""
    tournament = Tournament.query.get(tournament_id)
    if not tournament:
        return jsonify({'error': 'Tournament not found'}), 404
    if tournament.status != 'Pending':
        return jsonify({'error': 'Can only add players to a Pending tournament'}), 400

    data = request.get_json()
    if not data or not data.get('player_id'):
        return jsonify({'error': 'player_id is required'}), 400

    ace_pot_per_player = float(data.get('ace_pot_per_player', 1.00))

    try:
        registered, _ = _register_players_helper(
            tournament_id, tournament.tournament_date,
            [{'player_id': data['player_id'], 'bought_ace_pot': data.get('bought_ace_pot', False)}],
            ace_pot_per_player
        )
        db.session.commit()
        return jsonify({'registered': len(registered)}), 201
    except ValueError as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@tournaments_bp.route('/tournaments/<int:tournament_id>/players/<int:player_id>', methods=['DELETE'])
@require_role(app='putt', role='director')
def remove_player_from_pending(tournament_id, player_id):
    """Remove a player from a Pending tournament."""
    tournament = Tournament.query.get(tournament_id)
    if not tournament or tournament.status != 'Pending':
        return jsonify({'error': 'Tournament not found or not Pending'}), 404

    reg = TournamentRegistration.query.filter_by(
        tournament_id=tournament_id, player_id=player_id
    ).first()
    if not reg:
        return jsonify({'error': 'Player not registered'}), 404

    # Reverse ace pot entry if they bought in
    if reg.bought_ace_pot:
        ace_entry = AcePot.query.filter_by(tournament_id=tournament_id).order_by(AcePot.ace_pot_id.desc()).first()
        if ace_entry:
            ace_entry.amount -= Decimal(1.00)  # subtract one buy-in
            if ace_entry.amount <= 0:
                db.session.delete(ace_entry)

    db.session.delete(reg)
    db.session.commit()
    return jsonify({'success': True})


@tournaments_bp.route('/tournaments/<int:tournament_id>/register-players', methods=['POST'])
@require_role(app='putt', role='director')
def register_players_for_tournament(tournament_id):
    if tournament_id <= 0:
        return jsonify({'error': 'Invalid tournament ID'}), 400

    data = request.get_json()

    if not data or not data.get('registrations'):
        return jsonify({'error': 'Registrations list is required'}), 400

    tournament = Tournament.query.get(tournament_id)
    if not tournament:
        return jsonify({'error': 'Tournament not found'}), 404

    registrations = data['registrations']
    created_players = []
    errors = []

    # Create new players if needed
    for i, reg in enumerate(registrations):
        if 'player_name' in reg:
            division = reg.get('division', 'Am')
            if division not in ['Pro', 'Am', 'Junior']:
                errors.append(f'Registration {i + 1}: Division must be Pro, Am, or Junior')
                continue

            existing = RegisteredPlayer.query.filter_by(player_name=reg['player_name']).first()
            if not existing:
                player = RegisteredPlayer(
                    player_name=reg['player_name'],
                    nickname=reg.get('nickname'),
                    division=division,
                    seasonal_points=0,
                    seasonal_cash=0.00
                )
                db.session.add(player)
                db.session.flush()
                created_players.append(player)
                reg['player_id'] = player.player_id

    if errors:
        return jsonify({'errors': errors}), 400

    # Convert registrations to players format for helper
    players_data = []
    for reg in registrations:
        if 'player_id' in reg:
            players_data.append({
                'player_id': reg['player_id'],
                'bought_ace_pot': reg.get('bought_ace_pot', False)
            })

    try:
        registered_players, ace_pot_buyins = _register_players_helper(
            tournament_id, tournament.tournament_date, players_data
        )

        db.session.commit()

        result = {
            'tournament_id': tournament_id,
            'registered_players': len(registered_players),
            'ace_pot_buyins': ace_pot_buyins,
            'ace_pot_amount': ace_pot_buyins * 1.00,
            'players': [{
                'player_id': p.player_id,
                'player_name': p.player_name,
                'nickname': p.nickname,
                'division': p.division
            } for p in registered_players]
        }

        if created_players:
            result['new_players_created'] = len(created_players)

        return jsonify(result), 201

    except ValueError as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Failed to register players'}), 500


@tournaments_bp.route('/tournaments/<int:tournament_id>/matches', methods=['GET'])
def get_tournament_matches(tournament_id):
    matches = Match.query.filter_by(tournament_id=tournament_id).order_by(Match.match_order).all()
    return jsonify([{
        'match_id': m.match_id,
        'match_order': m.match_order,
        'round_type': m.round_type,
        'round_number': m.round_number,
        'team1_id': m.team1_id,
        'team2_id': m.team2_id,
        'team1_score': m.team1_score,
        'team2_score': m.team2_score,
        'match_status': m.match_status,
        'station_assignment': m.station_assignment,
        'winner_advances_to_match_id': m.winner_advances_to_match_id,
        'loser_advances_to_match_id': m.loser_advances_to_match_id
    } for m in matches])


@tournaments_bp.route('/tournaments/<int:tournament_id>/teams', methods=['GET'])
def get_tournament_teams(tournament_id):
    teams = Team.query.filter_by(tournament_id=tournament_id).all()
    result = []
    for team in teams:
        player1 = RegisteredPlayer.query.get(team.player1_id)
        player2 = RegisteredPlayer.query.get(team.player2_id) if team.player2_id else None

        result.append({
            'team_id': team.team_id,
            'player1_id': team.player1_id,
            'player1_name': player1.player_name if player1 else None,
            'player1_nickname': player1.nickname if player1 else None,
            'player2_id': team.player2_id,
            'player2_name': player2.player_name if player2 else None,
            'player2_nickname': player2.nickname if player2 else None,
            'is_ghost_team': team.is_ghost_team,
            'seed_number': team.seed_number,
            'final_place': team.final_place
        })

    return jsonify(result)


@tournaments_bp.route('/tournaments/<int:tournament_id>/status', methods=['PUT'])
@require_role(app='putt', role='director')
def update_tournament_status(tournament_id):
    data = request.get_json()

    if not data or 'status' not in data:
        return jsonify({'error': 'Status is required'}), 400

    new_status = data['status']
    if new_status not in ['Scheduled', 'In_Progress', 'Completed']:
        return jsonify({'error': 'Invalid status'}), 400

    tournament = Tournament.query.get(tournament_id)
    if not tournament:
        return jsonify({'error': 'Tournament not found'}), 404

    tournament.status = new_status
    db.session.commit()

    return jsonify({
        'tournament_id': tournament_id,
        'status': tournament.status
    })


@tournaments_bp.route('/tournaments/<int:tournament_id>', methods=['DELETE'])
@require_role(app='putt', role='admin')
def delete_tournament(tournament_id):
    try:
        # Clean up teammate history, seasonal points, and cash for any tournament
        tournament = Tournament.query.get(tournament_id)
        if tournament:
            _cleanup_teammate_history(tournament_id)
            _adjust_seasonal_points(tournament_id, reverse=True)
            _adjust_seasonal_cash(tournament_id, reverse=True)

        # Delete in dependency order
        Match.query.filter_by(tournament_id=tournament_id).delete()
        Team.query.filter_by(tournament_id=tournament_id).delete()
        TournamentRegistration.query.filter_by(tournament_id=tournament_id).delete()
        AcePot.query.filter_by(tournament_id=tournament_id).delete()

        if tournament:
            db.session.delete(tournament)
            db.session.commit()
            return jsonify({'message': 'Tournament deleted successfully'})
        else:
            return jsonify({'error': 'Tournament not found'}), 404
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Failed to delete tournament'}), 500


def _cleanup_teammate_history(tournament_id):
    """Remove teammate history entries for deleted tournament"""
    teams = Team.query.filter_by(tournament_id=tournament_id).all()

    for team in teams:
        if not team.is_ghost_team and team.player2_id:
            # Decrement history for both players
            for player_id, teammate_id in [(team.player1_id, team.player2_id), (team.player2_id, team.player1_id)]:
                history = TeamHistory.query.filter_by(player_id=player_id, teammate_id=teammate_id).first()

                if history:
                    history.times_paired -= 1
                    if history.times_paired <= 0:
                        db.session.delete(history)


def _adjust_seasonal_points(tournament_id, reverse=False):
    """Adjust seasonal points for tournament (add or subtract)"""
    # Only adjust points for completed tournaments (where points were actually awarded)
    tournament = Tournament.query.get(tournament_id)
    if not tournament or tournament.status != 'Completed':
        return

    teams = Team.query.filter_by(tournament_id=tournament_id).all()

    for team in teams:
        if team.points_earned:
            # Adjust player1 points
            if team.player1_id:
                player1 = RegisteredPlayer.query.get(team.player1_id)
                if player1:
                    if reverse:
                        player1.seasonal_points = max(0, player1.seasonal_points - team.points_earned)
                    else:
                        player1.seasonal_points += team.points_earned

            # Adjust player2 points
            if team.player2_id:
                player2 = RegisteredPlayer.query.get(team.player2_id)
                if player2:
                    if reverse:
                        player2.seasonal_points = max(0, player2.seasonal_points - team.points_earned)
                    else:
                        player2.seasonal_points += team.points_earned


def _adjust_seasonal_cash(tournament_id, reverse=False):
    """Adjust seasonal cash for tournament (add or subtract)"""
    tournament = Tournament.query.get(tournament_id)
    if not tournament or tournament.status != 'Completed':
        return

    registrations = TournamentRegistration.query.filter_by(tournament_id=tournament_id).all()
    total_participants = len(registrations)

    buy_in = float(tournament.buy_in_per_player) if tournament.buy_in_per_player is not None else 5.0
    total_payout_pot = buy_in * total_participants
    payout_config = tournament.payout_config

    if payout_config and payout_config.get('mode') == 'percentage':
        second_pct = float(payout_config.get('second_place_value', 30)) / 100.0
        second_place_payout = total_payout_pot * second_pct
        first_place_payout = total_payout_pot - second_place_payout
    elif payout_config and payout_config.get('mode') == 'fixed':
        second_place_payout = float(payout_config.get('second_place_value', 0))
        first_place_payout = total_payout_pot - second_place_payout
    else:
        second_place_payout = min(40, total_payout_pot - 40) if total_payout_pot > 40 else 0
        first_place_payout = total_payout_pot - second_place_payout

    if first_place_payout < second_place_payout:
        first_place_payout, second_place_payout = second_place_payout, first_place_payout

    # Find 1st and 2nd place teams
    first_place_team = Team.query.filter_by(tournament_id=tournament_id, final_place=1).first()

    # Include ace pot payout if applicable
    ace_pot_payout = 0
    if first_place_team and _is_undefeated_for_deletion(tournament_id, first_place_team.player1_id):
        ace_pot_entries = AcePot.query.filter_by(tournament_id=tournament_id).all()
        for entry in ace_pot_entries:
            if entry.amount < 0:
                ace_pot_payout = abs(float(entry.amount))
                break

    first_place_payout += ace_pot_payout

    for reg in registrations:
        player = RegisteredPlayer.query.get(reg.player_id)
        if player:
            player_team = Team.query.filter_by(tournament_id=tournament_id).filter(
                db.or_(Team.player1_id == reg.player_id, Team.player2_id == reg.player_id)
            ).first()

            if player_team:
                teammates_count = 2 if player_team.player2_id and not player_team.is_ghost_team else 1
                cash_adjustment = Decimal('0')

                if player_team.final_place == 1:
                    cash_adjustment = Decimal(str(first_place_payout / teammates_count))
                elif player_team.final_place == 2:
                    cash_adjustment = Decimal(str(second_place_payout / teammates_count))

                if reverse:
                    player.seasonal_cash = max(Decimal('0'), player.seasonal_cash - cash_adjustment)
                else:
                    player.seasonal_cash += cash_adjustment


def _is_undefeated_for_deletion(tournament_id, player_id):
    """Check if player's team went undefeated (for deletion)"""
    teams = Team.query.filter_by(tournament_id=tournament_id).filter(
        db.or_(Team.player1_id == player_id, Team.player2_id == player_id)
    ).all()

    for team in teams:
        matches = Match.query.filter_by(tournament_id=tournament_id).filter(
            db.or_(Match.team1_id == team.team_id, Match.team2_id == team.team_id)
        ).filter(Match.match_status == 'Completed').all()

        for match in matches:
            if ((match.team1_id == team.team_id and match.team1_score < match.team2_score) or
                    (match.team2_id == team.team_id and match.team2_score < match.team1_score)):
                return False

    return True
