"""
API endpoints for tournament management.
"""

from flask import Blueprint, jsonify, request, current_app
import datetime
from tournament_core.models import db, Tournament, TournamentParticipant, Player, Team
from backend.auth import login_required

tournaments_bp = Blueprint('tournaments_api', __name__)


def _rs():
    return current_app.rating_system


@tournaments_bp.route('/api/tournaments', methods=['GET'])
def get_tournaments():
    rs = _rs()
    # Current season = no season_id assigned
    db_tournaments = Tournament.query.filter_by(season_id=None).order_by(Tournament.date.desc()).all()
    in_memory = {t['id']: t for t in rs.tournaments if 'id' in t}

    result = []
    for t in db_tournaments:
        tid = t.tournament_id
        mem = in_memory.get(tid)
        result.append({
            'tournament_id': tid,
            'date': t.date.isoformat() if hasattr(t.date, 'isoformat') else str(t.date),
            'course': t.course,
            'teams': t.team_count,
            'status': t.status or 'Completed',
            'results': mem['results'] if mem else [],
        })
    return jsonify(result)


@tournaments_bp.route('/api/tournaments/<int:tid>', methods=['GET'])
def get_tournament(tid):
    t = Tournament.query.get(tid)
    if not t:
        return jsonify({'error': 'Tournament not found'}), 404

    participants = TournamentParticipant.query.filter_by(tournament_id=tid).all()
    players = []
    for p in participants:
        player = Player.query.get(p.player_id)
        if player:
            players.append({
                'name': player.name,
                'rating': float(player.rating),
                'ace_pot_buy_in': p.ace_pot_buy_in,
            })

    rs = _rs()
    mem = next((x for x in rs.tournaments if x.get('id') == tid), None)

    ace_pot_recipient = t.ace_pot_paid_to if t.ace_pot_paid else None

    # Include persisted team pairings (for In Progress tournaments)
    generated_teams = []
    if t.status == 'In Progress':
        db_teams = Team.query.filter_by(tournament_id=tid).order_by(Team.expected_position).all()
        for team in db_teams:
            p1 = Player.query.get(team.player1_id)
            p2 = Player.query.get(team.player2_id) if team.player2_id else None
            generated_teams.append({
                'player1': p1.name if p1 else 'Unknown',
                'player2': p2.name if p2 else 'Ghost Player',
                'team_rating': float(team.team_rating),
                'expected_position': float(team.expected_position),
            })

    return jsonify({
        'tournament_id': tid,
        'date': t.date.isoformat() if hasattr(t.date, 'isoformat') else str(t.date),
        'course': t.course,
        'teams': t.team_count,
        'status': t.status or 'Completed',
        'participants': players,
        'results': mem['results'] if mem else [],
        'generated_teams': generated_teams,
        'ace_pot_paid': t.ace_pot_paid,
        'ace_pot_recipient': ace_pot_recipient,
    })


@tournaments_bp.route('/api/tournaments/pending', methods=['POST'])
@login_required
def create_pending():
    """Create a pending tournament with course/date."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    course = data.get('course', '')
    date = data.get('date', datetime.datetime.now().strftime("%Y-%m-%d"))

    t = Tournament(date=date, course=course, team_count=0, status='Pending')
    db.session.add(t)
    db.session.commit()

    return jsonify({'tournament_id': t.tournament_id}), 201


@tournaments_bp.route('/api/tournaments/<int:tid>', methods=['PATCH'])
@login_required
def update_tournament(tid):
    t = Tournament.query.get(tid)
    if not t or t.status != 'Pending':
        return jsonify({'error': 'Tournament not found or not pending'}), 400
    data = request.get_json()
    if 'course' in data:
        t.course = data['course']
    if 'date' in data:
        t.date = data['date']
    db.session.commit()
    return jsonify({'message': 'Updated'})


@tournaments_bp.route('/api/tournaments/<int:tid>/players', methods=['POST'])
@login_required
def add_participant(tid):
    """Add a player to a pending tournament."""
    t = Tournament.query.get(tid)
    if not t or t.status != 'Pending':
        return jsonify({'error': 'Tournament not found or not pending'}), 400

    data = request.get_json()
    player_name = data.get('name', '')
    ace_pot = data.get('ace_pot_buy_in', False)

    rs = _rs()
    if not rs.player_exists(player_name):
        return jsonify({'error': f"Player '{player_name}' not found"}), 404

    pid = rs.db_manager._get_player_id_safe(player_name)
    if pid is None:
        return jsonify({'error': 'Player not found'}), 404

    existing = TournamentParticipant.query.filter_by(tournament_id=tid, player_id=pid).first()
    if existing:
        existing.ace_pot_buy_in = ace_pot
        db.session.commit()
        return jsonify({'message': 'Updated'}), 200

    tp = TournamentParticipant(tournament_id=tid, player_id=pid, ace_pot_buy_in=ace_pot)
    db.session.add(tp)
    db.session.commit()
    return jsonify({'message': 'Added'}), 201


@tournaments_bp.route('/api/tournaments/<int:tid>/players/<player_name>', methods=['DELETE'])
@login_required
def remove_participant(tid, player_name):
    """Remove a player from a pending tournament."""
    rs = _rs()
    pid = rs.db_manager._get_player_id_safe(player_name)
    if pid is None:
        return jsonify({'error': 'Player not found'}), 404

    tp = TournamentParticipant.query.filter_by(tournament_id=tid, player_id=pid).first()
    if tp:
        db.session.delete(tp)
        db.session.commit()
    return jsonify({'message': 'Removed'})


@tournaments_bp.route('/api/tournaments/<int:tid>/generate', methods=['POST'])
@login_required
def generate_teams(tid):
    """Generate teams for a pending tournament and set status to In Progress."""
    t = Tournament.query.get(tid)
    if not t or t.status != 'Pending':
        return jsonify({'error': 'Tournament not found or not pending'}), 400

    participants = TournamentParticipant.query.filter_by(tournament_id=tid).all()
    player_names = []
    for p in participants:
        player = Player.query.get(p.player_id)
        if player:
            player_names.append(player.name)

    if len(player_names) < 2:
        return jsonify({'error': 'Need at least 2 players'}), 400

    rs = _rs()
    try:
        teams = rs.generate_balanced_teams(player_names)
        predictions = rs.predict_tournament_outcome([tuple(team) for team in teams])
        t.team_count = len(teams)
        t.status = 'In Progress'

        # Persist generated teams
        for team in teams:
            p1_id = rs.db_manager._get_player_id_safe(team[0])
            p2_id = rs.db_manager._get_player_id_safe(team[1]) if team[1] != 'Ghost Player' else None
            team_rating = rs.calculate_team_rating(team[0], team[1])
            expected_pos = predictions[tuple(team)].get('expected_position', 0)
            db.session.add(Team(
                tournament_id=tid, player1_id=p1_id, player2_id=p2_id,
                is_ghost_team=(team[1] == 'Ghost Player'),
                expected_position=expected_pos, team_rating=team_rating,
            ))

        db.session.commit()

        results = [{
            'player1': team[0], 'player2': team[1],
            'team_rating': rs.calculate_team_rating(team[0], team[1]),
            'expected_position': predictions[tuple(team)].get('expected_position', 0),
        } for team in teams]
        return jsonify({'tournament_id': tid, 'teams': results})
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@tournaments_bp.route('/api/tournaments/<int:tid>/record', methods=['POST'])
@login_required
def record_results(tid):
    """Record scores for an in-progress tournament, completing it."""
    t = Tournament.query.get(tid)
    if not t or t.status != 'In Progress':
        return jsonify({'error': 'Tournament not found or not in progress'}), 400

    data = request.get_json()
    team_results = data.get('team_results', [])
    if not team_results:
        return jsonify({'error': 'No results provided'}), 400

    # Payout config
    payout_config = data.get('payout_config', {})
    buy_in = payout_config.get('buy_in_per_player', 0)
    second_place_fixed = payout_config.get('second_place', 40)
    third_place_fixed = payout_config.get('third_place', 20)

    formatted = []
    for tr in team_results:
        if 'player1' in tr and 'player2' in tr and 'score' in tr:
            try:
                formatted.append(((tr['player1'], tr['player2']), int(tr['score'])))
            except ValueError:
                return jsonify({'error': f"Invalid score for {tr['player1']} & {tr['player2']}"}), 400
    if not formatted:
        return jsonify({'error': 'No valid results'}), 400

    # Calculate payouts
    total_players = sum(2 if p2 != 'Ghost Player' else 1 for (p1, p2), _ in formatted)
    pot = buy_in * total_players
    third_payout = third_place_fixed if pot > 0 and len(formatted) >= 3 else 0
    second_payout = second_place_fixed if pot > 0 and len(formatted) >= 2 else 0
    first_payout = pot - second_payout - third_payout if pot > 0 else 0

    # 1st always gets the highest — swap with 2nd if needed
    if first_payout < second_payout:
        first_payout, second_payout = second_payout, first_payout

    manual_payouts = data.get('manual_payouts')

    rs = _rs()

    try:
        # Resolve positions (handles ties)
        positions = rs.resolve_tournament_positions(formatted)
        predictions = rs.predict_tournament_outcome([team for team, _ in formatted])

        # Update existing Team records with position and score
        db_teams = Team.query.filter_by(tournament_id=tid).all()
        team_lookup = {}
        for team in db_teams:
            p1 = Player.query.get(team.player1_id)
            p2 = Player.query.get(team.player2_id) if team.player2_id else None
            key = (p1.name if p1 else '', p2.name if p2 else 'Ghost Player')
            team_lookup[key] = team

        # Build in-memory tournament record for rs.tournaments
        tournament_record = {
            'id': tid,
            'date': t.date.isoformat() if hasattr(t.date, 'isoformat') else str(t.date),
            'course': t.course,
            'teams': len(formatted),
            'results': [],
        }

        for position, (team, score) in positions:
            player1, player2 = team
            # Normalize names
            if player1 != "Ghost Player":
                player1 = rs.get_player_name(player1)
            if player2 != "Ghost Player":
                player2 = rs.get_player_name(player2)

            team_rating = rs.calculate_team_rating(player1, player2)
            expected_position = predictions[team]['expected_position']
            position_diff = expected_position - position

            midpoint = len(formatted) / 2
            max_diff = len(formatted) - midpoint
            mid_diff = midpoint - position
            overall_modifier = mid_diff * abs(mid_diff / max_diff)

            tournament_record['results'].append({
                'team': [player1, player2], 'score': score, 'position': position,
                'expected_position': expected_position, 'team_rating': team_rating,
            })

            # Update the existing Team row
            db_team = team_lookup.get((player1, player2))
            if db_team:
                db_team.position = position
                db_team.score = score
                db_team.team_rating = team_rating
                db_team.expected_position = expected_position

            # Update player ratings
            for player in [player1, player2]:
                if player == "Ghost Player":
                    continue
                k_factor = rs.get_k_factor(player)
                player_data = rs.get_player(player)
                old_rating = player_data['rating']
                tournament_bonus = 1 + (len(formatted) - 4) * 0.05
                adjustment = k_factor * (position_diff + overall_modifier) * tournament_bonus
                new_rating = old_rating + adjustment

                player_data['rating'] = new_rating
                player_data['tournaments_played'] += 1
                player_data['history'].append({
                    'tournament_date': t.date.isoformat() if hasattr(t.date, 'isoformat') else str(t.date),
                    'old_rating': old_rating, 'new_rating': new_rating,
                    'change': new_rating - old_rating, 'position': position,
                    'expected_position': expected_position, 'score': score,
                    'with_ghost': "Ghost Player" in [player1, player2],
                })

                rs.db_manager.update_player_rating(player, new_rating)
                rs.db_manager.increment_player_tournaments(player)
                rs.db_manager.add_player_history(
                    player, tid, old_rating, new_rating,
                    position, expected_position, score,
                    "Ghost Player" in [player1, player2],
                )

        # Mark tournament completed
        t.status = 'Completed'
        rs.tournaments.append(tournament_record)

        # Handle payouts
        teams = Team.query.filter_by(tournament_id=tid).order_by(Team.position).all()

        if manual_payouts:
            for mp in manual_payouts:
                for team in teams:
                    p1 = Player.query.get(team.player1_id)
                    p2 = Player.query.get(team.player2_id) if team.player2_id else None
                    p1_name = p1.name if p1 else ''
                    p2_name = p2.name if p2 else 'Ghost Player'
                    if p1_name == mp['player1'] and p2_name == mp['player2']:
                        amt = float(mp['payout'])
                        team.payout = amt
                        if amt > 0:
                            is_ghost = not team.player2_id
                            per_player = amt if is_ghost else amt / 2
                            if p1:
                                p1.seasonal_cash = float(p1.seasonal_cash) + per_player
                            if not is_ghost and p2:
                                p2.seasonal_cash = float(p2.seasonal_cash) + per_player
                        break
        else:
            from collections import Counter
            position_counts = Counter(team.position for team in teams)
            paid_positions = [1, 2] if len(formatted) < 3 else [1, 2, 3]
            has_tie = any(position_counts.get(p, 0) > 1 for p in paid_positions)

            if has_tie:
                db.session.commit()
                rs.load_data()
                payout_teams = []
                for team in teams:
                    if team.position in paid_positions:
                        p1 = Player.query.get(team.player1_id)
                        p2 = Player.query.get(team.player2_id) if team.player2_id else None
                        payout_teams.append({
                            'player1': p1.name if p1 else 'Unknown',
                            'player2': p2.name if p2 else 'Ghost Player',
                            'position': team.position, 'score': team.score,
                        })
                return jsonify({
                    'message': f'Tournament recorded with {len(formatted)} teams',
                    'tournament_id': tid,
                    'needs_manual_payout': True,
                    'pot': pot, 'first_payout': first_payout,
                    'second_payout': second_payout, 'third_payout': third_payout,
                    'tied_teams': payout_teams,
                }), 201

            for team in teams:
                payout_amount = {1: first_payout, 2: second_payout, 3: third_payout}.get(team.position, 0)
                if payout_amount > 0:
                    team.payout = payout_amount
                    is_ghost = team.is_ghost_team or not team.player2_id
                    per_player = payout_amount if is_ghost else payout_amount / 2
                    p1 = Player.query.get(team.player1_id)
                    if p1:
                        p1.seasonal_cash = float(p1.seasonal_cash) + per_player
                    if not is_ghost and team.player2_id:
                        p2 = Player.query.get(team.player2_id)
                        if p2:
                            p2.seasonal_cash = float(p2.seasonal_cash) + per_player

        db.session.commit()
        rs.load_data()

        return jsonify({
            'message': f'Tournament recorded with {len(formatted)} teams',
            'tournament_id': tid,
        }), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400


@tournaments_bp.route('/api/tournaments/<int:tid>/payouts', methods=['POST'])
@login_required
def apply_manual_payouts(tid):
    """Apply manually specified payouts (for tie resolution)."""
    t = Tournament.query.get(tid)
    if not t:
        return jsonify({'error': 'Tournament not found'}), 404

    data = request.get_json()
    payouts = data.get('payouts', [])

    teams = Team.query.filter_by(tournament_id=tid).all()
    for mp in payouts:
        amt = float(mp.get('payout', 0))
        for team in teams:
            p1 = Player.query.get(team.player1_id)
            p2 = Player.query.get(team.player2_id) if team.player2_id else None
            p1_name = p1.name if p1 else ''
            p2_name = p2.name if p2 else 'Ghost Player'
            if p1_name == mp['player1'] and p2_name == mp['player2']:
                team.payout = amt
                if amt > 0:
                    is_ghost = not team.player2_id
                    per_player = amt if is_ghost else amt / 2
                    if p1:
                        p1.seasonal_cash = float(p1.seasonal_cash) + per_player
                    if not is_ghost and p2:
                        p2.seasonal_cash = float(p2.seasonal_cash) + per_player
                break

    db.session.commit()
    rs = _rs()
    rs.load_data()
    return jsonify({'message': 'Payouts applied'})


@tournaments_bp.route('/api/tournaments/<int:tid>', methods=['DELETE'])
@login_required
def delete_tournament(tid):
    t = Tournament.query.get(tid)
    if not t:
        return jsonify({'error': 'Not found'}), 404
    TournamentParticipant.query.filter_by(tournament_id=tid).delete()
    Team.query.filter_by(tournament_id=tid).delete()
    db.session.delete(t)
    db.session.commit()
    return jsonify({'message': 'Deleted'})

@tournaments_bp.route('/api/tournaments/<int:tid>/reset', methods=['POST'])
@login_required
def reset_tournament(tid):
    t = Tournament.query.get(tid)
    if not t:
        return jsonify({'error': 'Not found'}), 404
    if t.status != 'In Progress':
        return jsonify({'error': 'Invalid status, Tournament must be in progress to edit'}), 403
    Team.query.filter_by(tournament_id=tid).delete()
    t.team_count = 0
    t.status = 'Pending'
    db.session.commit()
    return jsonify({'message': 'Teams Reset'})


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
def generate_teams_standalone():
    """Standalone team generation (not tied to a tournament)."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    players = data.get('players', [])
    if len(players) < 2:
        return jsonify({'error': 'At least 2 players are required'}), 400

    rs = _rs()
    try:
        teams = rs.generate_balanced_teams(players)
        predictions = rs.predict_tournament_outcome([tuple(t) for t in teams])
        results = [{
            'player1': t[0], 'player2': t[1],
            'team_rating': rs.calculate_team_rating(t[0], t[1]),
            'expected_position': predictions[tuple(t)].get('expected_position', 0),
        } for t in teams]
        return jsonify(results)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
