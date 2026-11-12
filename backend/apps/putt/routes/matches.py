"""DG-Putt match scoring, bracket generation, and progression.

Ported from the standalone DG-Putt repo. The double-elimination bracket logic
is preserved verbatim; only imports (putt_* models via aliases), auth
(two-axis require_role(app='putt')), the /api/putt URL prefix, and error
handling were adjusted during the fold-in. Live updates emit over SocketIO via
current_app.extensions['socketio'].
"""

import math
from decimal import Decimal

from flask import Blueprint, jsonify, request, current_app
from sqlalchemy import text

from backend.models import (
    db,
    PuttTournament as Tournament,
    PuttTeam as Team,
    PuttMatch as Match,
    PuttPlayer as RegisteredPlayer,
    PuttTeamHistory as TeamHistory,
    PuttRegistration as TournamentRegistration,
    PuttAcePot as AcePot,
)
from backend.shared.auth import require_role

matches_bp = Blueprint('putt_matches', __name__, url_prefix='/api/putt')


def _emit_match_update(tournament_id, payload):
    """Emit a match_updated event to the tournament room, if SocketIO is up."""
    socketio = current_app.extensions.get('socketio')
    if socketio:
        socketio.emit('match_updated', payload, room=f'tournament_{tournament_id}')


@matches_bp.route('/tournaments/<int:tournament_id>/matches/<int:match_id>/start', methods=['POST'])
@require_role(app='putt', role='director')
def start_match(tournament_id, match_id):
    match = Match.query.filter_by(tournament_id=tournament_id, match_id=match_id).first()
    if not match:
        return jsonify({'error': 'Match not found'}), 404

    if match.match_status != 'Scheduled':
        return jsonify({'error': 'Match is not scheduled'}), 400

    # Get tournament to check available stations
    tournament = Tournament.query.get(tournament_id)
    max_stations = tournament.stations if tournament else 6

    # Find first available station using tournament's station count
    occupied_stations = db.session.query(Match.station_assignment).filter(
        Match.tournament_id == tournament_id,
        Match.match_status == 'In_Progress'
    ).all()

    occupied = {station[0] for station in occupied_stations if station[0]}
    available_station = next((i for i in range(1, max_stations + 1) if i not in occupied), None)

    if not available_station:
        return jsonify({'error': 'No stations available'}), 400

    match.match_status = 'In_Progress'
    match.station_assignment = available_station

    try:
        db.session.commit()

        _emit_match_update(tournament_id, {
            'tournament_id': tournament_id,
            'match_id': match.match_id,
            'status': match.match_status,
            'station': match.station_assignment
        })

        return jsonify({
            'match_id': match.match_id,
            'status': match.match_status,
            'station': match.station_assignment
        })
    except Exception:
        db.session.rollback()
        return jsonify({'error': 'Failed to start match'}), 500


@matches_bp.route('/tournaments/<int:tournament_id>/matches/<int:match_id>/score', methods=['POST'])
@require_role(app='putt', role='director')
def score_match(tournament_id, match_id):
    data = request.get_json()

    match = Match.query.filter_by(tournament_id=tournament_id, match_id=match_id).first()
    if not match:
        return jsonify({'error': 'Match not found'}), 404

    # Validate match can be scored
    validation_error = _validate_match_scoring(match, data)
    if validation_error:
        return validation_error

    # Check for rescore and store old results
    is_rescore, old_winner_id, old_loser_id = _check_rescore_status(match)

    # Process the match scoring
    winner_team_id, loser_team_id = _process_match_scoring(match, data)

    # Handle rollbacks if needed
    rollback_results = []
    if is_rescore and old_winner_id and (old_winner_id != winner_team_id):
        rollback_results = _rollback_match_advancements(match, old_winner_id, old_loser_id)

    # Advance teams to next matches
    advancement_results = _advance_teams(match, tournament_id, winner_team_id, loser_team_id)

    # Handle post-match processing
    _handle_post_match_processing(match, tournament_id, winner_team_id, loser_team_id)

    # Handle championship match rescoring if this is a rescore
    if is_rescore and match.round_type == 'Championship' and match.round_number == 0:
        _handle_championship_rescore(match, tournament_id, winner_team_id, loser_team_id, is_rescore=True)

    try:
        db.session.commit()

        _emit_match_update(tournament_id, {
            'tournament_id': tournament_id,
            'match_id': match.match_id,
            'status': match.match_status,
            'team1_score': match.team1_score,
            'team2_score': match.team2_score,
            'winner_team_id': winner_team_id,
            'is_rescore': is_rescore
        })

        return jsonify({
            'match_id': match.match_id,
            'status': match.match_status,
            'team1_score': match.team1_score,
            'team2_score': match.team2_score,
            'winner_team_id': winner_team_id,
            'is_rescore': is_rescore,
            'advancements': advancement_results,
            'rollbacks': rollback_results
        })
    except Exception as e:
        current_app.logger.exception(
            "score_match failed (tournament=%s match=%s)", tournament_id, match_id
        )
        db.session.rollback()
        return jsonify({'error': 'Failed to score match'}), 500


def _validate_match_scoring(match, data):
    """Validate that a match can be scored"""
    if match.team2_id is None:
        if match.match_status not in ['Pending', 'Scheduled', 'Completed']:
            return jsonify({'error': f'Bye match cannot be advanced (status: {match.match_status})'}), 400
    else:
        if match.match_status not in ['In_Progress', 'Completed']:
            return jsonify({'error': 'Match is not in progress or completed'}), 400

        if not data or 'team1_score' not in data or 'team2_score' not in data:
            return jsonify({'error': 'Missing score data'}), 400

        try:
            team1_score = int(data['team1_score'])
            team2_score = int(data['team2_score'])
            if team1_score < 0 or team2_score < 0:
                return jsonify({'error': 'Scores must be non-negative'}), 400
            if team1_score == team2_score:
                return jsonify({'error': 'Matches cannot end in a tie'}), 400
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid score format'}), 400

    return None


def _check_rescore_status(match):
    """Check if this is a rescore and return old results"""
    is_rescore = match.match_status == 'Completed'
    old_winner_id = None
    old_loser_id = None

    if is_rescore and match.team1_score is not None and match.team2_score is not None:
        old_winner_id = match.team1_id if match.team1_score > match.team2_score else match.team2_id
        old_loser_id = match.team2_id if match.team1_score > match.team2_score else match.team1_id

    return is_rescore, old_winner_id, old_loser_id


def _process_match_scoring(match, data):
    """Process the actual match scoring and return winner/loser"""
    if match.team2_id is None:
        # Bye match
        if not match.team1_id:
            raise ValueError('No team to advance')

        match.team1_score = 1
        match.team2_score = 0
        match.match_status = 'Completed'
        match.station_assignment = None

        return match.team1_id, None
    else:
        # Regular match
        team1_score = int(data['team1_score'])
        team2_score = int(data['team2_score'])

        match.team1_score = team1_score
        match.team2_score = team2_score
        match.match_status = 'Completed'
        match.station_assignment = None

        if team1_score > team2_score:
            return match.team1_id, match.team2_id
        else:
            return match.team2_id, match.team1_id


def _advance_teams(match, tournament_id, winner_team_id, loser_team_id):
    """Advance teams to next matches and return advancement results"""
    advancement_results = []

    if match.winner_advances_to_match_id and winner_team_id:
        next_match = Match.query.filter_by(tournament_id=tournament_id, match_id=match.winner_advances_to_match_id).first()
        if next_match:
            # idempotent: don't re-place a team already in this match
            if winner_team_id in (next_match.team1_id, next_match.team2_id):
                pass
            elif not next_match.team1_id:
                next_match.team1_id = winner_team_id
                advancement_results.append({'team_id': winner_team_id, 'type': 'winner', 'advanced_to_match_id': next_match.match_id})
            elif not next_match.team2_id:
                next_match.team2_id = winner_team_id
                advancement_results.append({'team_id': winner_team_id, 'type': 'winner', 'advanced_to_match_id': next_match.match_id})
            if next_match.team1_id and next_match.team2_id and next_match.match_status == 'Pending':
                next_match.match_status = 'Scheduled'

    if match.loser_advances_to_match_id and loser_team_id:
        next_match = Match.query.filter_by(tournament_id=tournament_id, match_id=match.loser_advances_to_match_id).first()
        if next_match:
            if loser_team_id in (next_match.team1_id, next_match.team2_id):
                pass
            if not next_match.team1_id:
                next_match.team1_id = loser_team_id
                advancement_results.append({'team_id': loser_team_id, 'type': 'loser', 'advanced_to_match_id': next_match.match_id})
            elif not next_match.team2_id:
                next_match.team2_id = loser_team_id
                advancement_results.append({'team_id': loser_team_id, 'type': 'loser', 'advanced_to_match_id': next_match.match_id})

            if next_match.team1_id and next_match.team2_id and next_match.match_status == 'Pending':
                next_match.match_status = 'Scheduled'

    return advancement_results


def _handle_post_match_processing(match, tournament_id, winner_team_id, loser_team_id):
    """Handle auto-advancement, championship completion, and tournament completion"""
    _auto_advance_byes(tournament_id)

    if match.round_type == 'Championship':
        _handle_championship_completion(match, winner_team_id, loser_team_id)
    else:
        remaining_matches = Match.query.filter_by(
            tournament_id=tournament_id,
            match_status='Pending'
        ).filter(Match.team1_id.isnot(None)).count()

        scheduled_matches = Match.query.filter_by(
            tournament_id=tournament_id,
            match_status='Scheduled'
        ).count()

        if remaining_matches == 0 and scheduled_matches == 0:
            tournament = Tournament.query.get(tournament_id)
            tournament.status = 'Completed'
            _process_tournament_completion(tournament_id)


def _handle_championship_rescore(match, tournament_id, winner_team_id, loser_team_id, is_rescore=False):
    """Handle creation/removal of second championship match based on first championship result"""
    # Only run this logic during actual rescores, not initial scoring
    if not is_rescore:
        return

    # Check if second championship match exists
    second_championship = Match.query.filter_by(
        tournament_id=tournament_id,
        round_type='Championship',
        round_number=1
    ).first()

    # If WB winner (team1) won, remove second championship match if it exists
    if winner_team_id == match.team1_id:
        if second_championship:
            db.session.delete(second_championship)
    # If LB winner (team2) won, create second championship match if it doesn't exist
    else:
        if not second_championship:
            # Get the highest match_id to continue numbering
            last_match = Match.query.filter_by(tournament_id=tournament_id).order_by(Match.match_id.desc()).first()
            next_match_id = (last_match.match_id + 1) if last_match else 1

            final_match = Match(
                tournament_id=tournament_id,
                match_id=next_match_id,
                stage_type='Finals',
                round_type='Championship',
                round_number=1,
                position_in_round=0,
                stage_match_number=next_match_id,
                match_order=next_match_id,
                team1_id=match.team1_id,  # WB winner gets another chance
                team2_id=match.team2_id,  # LB winner
                match_status='Scheduled'
            )
            db.session.add(final_match)


@matches_bp.route('/tournaments/<int:tournament_id>/generate-matches', methods=['POST'])
@require_role(app='putt', role='director')
def generate_matches(tournament_id):
    data = request.get_json() or {}

    tournament = Tournament.query.get(tournament_id)
    if not tournament:
        return jsonify({'error': 'Tournament not found'}), 404

    if tournament.status != 'Scheduled':
        return jsonify({'error': f'Cannot generate matches for tournament with status: {tournament.status}'}), 400

    teams = Team.query.filter_by(tournament_id=tournament_id).all()
    if len(teams) < 4:
        return jsonify({'error': 'Need at least 4 teams'}), 400

    matches = _create_winners_bracket_matches(tournament_id, teams)
    _create_loser_bracket_matches(tournament_id, matches, len(teams))
    _set_advancement_paths(matches)
    _seed_teams_and_handle_byes(matches, teams)
    _set_match_order(matches)

    # Single database transaction
    db.session.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
    db.session.add_all(matches)
    db.session.commit()
    db.session.execute(text("SET FOREIGN_KEY_CHECKS = 1"))

    return jsonify({'tournament_id': tournament_id, 'matches_created': len(matches)}), 201


def _create_winners_bracket_matches(tournament_id, teams):
    """Create all bracket matches (winners, losers, championship)"""
    bracket_size = 1 << (len(teams) - 1).bit_length() if len(teams) & (len(teams) - 1) else len(teams)
    wb_rounds = int(math.log2(bracket_size))

    matches = []
    match_id = 1

    # Create winners bracket matches
    for round_num in range(wb_rounds):
        matches_in_round = bracket_size >> (round_num + 1)
        for pos in range(matches_in_round):
            matches.append(Match(
                tournament_id=tournament_id, match_id=match_id, stage_type='Group_A',
                round_type='Winners', round_number=round_num, position_in_round=pos,
                stage_match_number=match_id, match_order=match_id, match_status='Pending'
            ))
            match_id += 1
    return matches


def _create_loser_bracket_matches(tournament_id, matches, team_count):
    wb_round = 0
    lb_round = 0
    prev_round_count = 0
    match_id = matches[len(matches) - 1].match_id + 1
    bracket_size = 1 << (team_count - 1).bit_length() if team_count & (team_count - 1) else team_count
    loserMatchesNeeded = bracket_size - 2

    # Standard alternating pattern
    while (loserMatchesNeeded > 0):
        if lb_round == 0 or lb_round % 2 == 1:  # odd rounds get WB losers
            matches_in_round = math.ceil(((bracket_size >> (wb_round + 1)) + prev_round_count) / 2)
            wb_round += 1
            prev_round_count = matches_in_round

        else:  # even rounds resolve LB matches
            matches_in_round = math.ceil(prev_round_count / 2)
            prev_round_count = matches_in_round

        for pos in range(matches_in_round):
            matches.append(Match(
                tournament_id=tournament_id,
                match_id=match_id,
                stage_type='Group_A',
                round_type='Losers',
                round_number=lb_round,
                position_in_round=pos + 1,
                stage_match_number=match_id,
                match_order=match_id,
                match_status='Pending'
            ))
            loserMatchesNeeded -= 1
            match_id += 1
        lb_round += 1
    _create_championship_match(tournament_id=tournament_id, match_id=match_id, matches=matches)


def _create_championship_match(tournament_id, match_id, matches):
    championship = Match(
        tournament_id=tournament_id, match_id=match_id, stage_type='Finals',
        round_type='Championship', round_number=0, position_in_round=0,
        stage_match_number=match_id, match_order=match_id, match_status='Pending'
    )
    matches.append(championship)


def _set_advancement_paths(matches):
    """Set winner and loser advancement paths for all matches"""
    wb_matches = [m for m in matches if m.round_type == 'Winners']
    lb_matches = [m for m in matches if m.round_type == 'Losers']
    championship = next(m for m in matches if m.round_type == 'Championship')

    # Winners bracket progression
    for match in wb_matches:
        if match.round_number < max(m.round_number for m in wb_matches):
            next_pos = match.position_in_round // 2
            next_match = next((m for m in wb_matches
                               if m.round_number == match.round_number + 1
                               and m.position_in_round == next_pos), None)
            if next_match:
                match.winner_advances_to_match_id = next_match.match_id
        else:
            match.winner_advances_to_match_id = championship.match_id

    # Group losers matches by round
    lb_by_round = {}
    for match in lb_matches:
        if match.round_number not in lb_by_round:
            lb_by_round[match.round_number] = []
        lb_by_round[match.round_number].append(match)

    # Sort each round by match_id
    for round_num in lb_by_round:
        lb_by_round[round_num].sort(key=lambda x: x.match_id)

    # Track match capacity
    match_capacity = {match.match_id: 2 for match in lb_matches}
    match_assigned = {match.match_id: 0 for match in lb_matches}

    # Set LB internal progressions and track assignments
    for round_num in sorted(lb_by_round.keys()):
        current_round = lb_by_round[round_num]
        next_round_num = round_num + 1

        if next_round_num in lb_by_round:
            next_round = lb_by_round[next_round_num]
            for i, match in enumerate(current_round):
                target_match = next_round[i % len(next_round)]
                match.winner_advances_to_match_id = target_match.match_id
                match_assigned[target_match.match_id] += 1
        else:
            for match in current_round:
                match.winner_advances_to_match_id = championship.match_id

    # WB losers drop to LB (only odd rounds accept WB losers)
    for wb_match in sorted(wb_matches, key=lambda x: x.match_id):
        if wb_match.round_number == max(m.round_number for m in wb_matches):
            target_round = max(lb_by_round.keys())
        else:
            target_round = 0 if wb_match.round_number == 0 else wb_match.round_number * 2 - 1

        if target_round in lb_by_round:
            target_matches = lb_by_round[target_round]
            matches_to_iterate = reversed(target_matches) if target_round == 1 else target_matches
            for target_match in matches_to_iterate:
                if match_assigned[target_match.match_id] < match_capacity[target_match.match_id]:
                    wb_match.loser_advances_to_match_id = target_match.match_id
                    match_assigned[target_match.match_id] += 1
                    break


def _seed_teams_and_handle_byes(matches, teams):
    """Seed teams into first round and handle bye advancement"""
    wb_matches = [m for m in matches if m.round_type == 'Winners']
    bracket_size = 1 << (len(teams) - 1).bit_length() if len(teams) & (len(teams) - 1) else len(teams)
    byes_needed = bracket_size - len(teams)

    first_round = [m for m in wb_matches if m.round_number == 0]
    bye_matches_to_remove = []

    # Handle byes
    for i in range(byes_needed):
        first_round[i].team1_id = teams[i].team_id
        first_round[i].match_status = 'Scheduled'
        # Auto-advance bye teams
        if first_round[i].winner_advances_to_match_id:
            next_match = next((m for m in matches if m.match_id == first_round[i].winner_advances_to_match_id), None)
            if next_match:
                if next_match.team1_id is None:
                    next_match.team1_id = teams[i].team_id
                elif next_match.team2_id is None:
                    next_match.team2_id = teams[i].team_id
                if next_match.team1_id and next_match.team2_id:
                    next_match.match_status = 'Scheduled'
        bye_matches_to_remove.append(first_round[i])

    # Seed real matches
    team_idx = byes_needed
    for i in range(byes_needed, len(first_round)):
        if team_idx < len(teams):
            first_round[i].team1_id = teams[team_idx].team_id
            team_idx += 1
        if team_idx < len(teams):
            first_round[i].team2_id = teams[team_idx].team_id
            first_round[i].match_status = 'Scheduled'
            team_idx += 1

    # Remove bye matches
    for bye_match in bye_matches_to_remove:
        matches.remove(bye_match)

    # Handle losers bracket byes
    _handle_losers_bracket_byes(matches, byes_needed)


def _handle_losers_bracket_byes(matches, byes_needed):
    """Handle losers bracket adjustments when winners bracket has byes"""
    if byes_needed == 0:
        return

    lb_matches = [m for m in matches if m.round_type == 'Losers' and m.round_number == 0]
    wb_matches = [m for m in matches if m.round_type == 'Winners' and m.round_number == 0]

    for lb_match in lb_matches:
        # Find WB matches that feed into this LB match
        feeding_wb_matches = [wb for wb in wb_matches if wb.loser_advances_to_match_id == lb_match.match_id]

        if len(feeding_wb_matches) <= 1:
            if (len(feeding_wb_matches) == 0):
                matches.remove(lb_match)
            else:
                # Single parent - redirect its loser to where this LB match winner would go
                parent_wb = feeding_wb_matches[0]
                parent_wb.loser_advances_to_match_id = lb_match.winner_advances_to_match_id
                matches.remove(lb_match)


def _set_match_order(matches):
    """Set match order for scheduling"""
    non_championship_matches = [m for m in matches if m.round_type != 'Championship']
    non_championship_matches.sort(key=lambda m: (m.round_number, m.round_type == 'Losers', m.match_id))
    for i, match in enumerate(non_championship_matches, 1):
        match.match_order = i


def _rollback_match_advancements(match, old_winner_id, old_loser_id):
    """Remove teams from subsequent matches when re-scoring"""

    rollbacks = []

    # Remove old winner from winner advancement match
    if match.winner_advances_to_match_id:
        target_match = Match.query.filter_by(tournament_id=match.tournament_id, match_id=match.winner_advances_to_match_id).first()
        if target_match:
            if target_match.team1_id == old_winner_id:
                target_match.team1_id = None
                rollbacks.append({'team_id': old_winner_id, 'removed_from_match_id': target_match.match_id})
            elif target_match.team2_id == old_winner_id:
                target_match.team2_id = None
                rollbacks.append({'team_id': old_winner_id, 'removed_from_match_id': target_match.match_id})

    # Remove old loser from loser advancement match
    if match.loser_advances_to_match_id:
        target_match = Match.query.filter_by(tournament_id=match.tournament_id, match_id=match.loser_advances_to_match_id).first()
        if target_match:
            if target_match.team1_id == old_loser_id:
                target_match.team1_id = None
                rollbacks.append({'team_id': old_loser_id, 'removed_from_match_id': target_match.match_id})
            elif target_match.team2_id == old_loser_id:
                target_match.team2_id = None
                rollbacks.append({'team_id': old_loser_id, 'removed_from_match_id': target_match.match_id})

    return rollbacks


def _auto_advance_byes(tournament_id):
    """Auto-advance teams in bye matches (matches with only one team that won't get a second team)"""
    matches = Match.query.filter_by(tournament_id=tournament_id).all()

    for match in matches:
        # Skip if match is already completed or in progress
        if match.match_status not in ['Pending']:
            continue

        # Check if this is a bye match (has one team but no second team will come)
        if match.team1_id and not match.team2_id:
            # Count how many matches feed into this match
            feeding_matches = [m for m in matches if
                               m.winner_advances_to_match_id == match.match_id or
                               m.loser_advances_to_match_id == match.match_id]

            # If only one match feeds into this one and it's completed, this is a bye
            completed_feeding = [m for m in feeding_matches if m.match_status == 'Completed']

            if len(feeding_matches) == 1 and len(completed_feeding) == 1:
                # This is a true bye - auto-advance
                match.team1_score = 1
                match.team2_score = 0
                match.match_status = 'Completed'

                # Advance the team to the next match
                if match.winner_advances_to_match_id:
                    next_match = next((m for m in matches if m.match_id == match.winner_advances_to_match_id), None)
                    if next_match:
                        if not next_match.team1_id:
                            next_match.team1_id = match.team1_id
                        elif not next_match.team2_id:
                            next_match.team2_id = match.team1_id

                        # Update status to Scheduled if both teams are now assigned
                        if next_match.team1_id and next_match.team2_id and next_match.match_status == 'Pending':
                            next_match.match_status = 'Scheduled'
            elif len(feeding_matches) == 0:
                # This match has a seeded team but no feeding matches - it's waiting for another team
                pass  # Keep as Pending until second team arrives


def _handle_championship_completion(match, winner_team_id, loser_team_id):
    """Handle championship match completion - either end tournament or create final match"""
    # Check if this was WB winner vs LB winner (first championship match)
    if match.round_number == 0:
        # If WB winner won (team1), tournament is complete
        if winner_team_id == match.team1_id:
            tournament = Tournament.query.get(match.tournament_id)
            tournament.status = 'Completed'
            _process_tournament_completion(match.tournament_id)
        else:
            # LB winner won, create final championship match
            next_match_id = match.match_id + 1

            final_match = Match(
                tournament_id=match.tournament_id,
                match_id=next_match_id,
                stage_type='Finals',
                round_type='Championship',
                round_number=1,
                position_in_round=0,
                stage_match_number=next_match_id,
                match_order=next_match_id,
                team1_id=match.team1_id,  # WB winner gets another chance
                team2_id=match.team2_id,  # LB winner
                match_status='Scheduled'
            )
            db.session.add(final_match)
    else:
        # This was the final championship match, tournament is complete
        tournament = Tournament.query.get(match.tournament_id)
        tournament.status = 'Completed'
        _process_tournament_completion(match.tournament_id)


def _process_tournament_completion(tournament_id):
    """Process all completion tasks for a tournament"""
    _calculate_final_places(tournament_id)
    _update_teammate_history(tournament_id)
    _update_seasonal_points(tournament_id)
    _distribute_cash_payouts(tournament_id)


def _calculate_final_places(tournament_id):
    """Calculate and set final places for all teams"""
    # Find championship matches to determine 1st and 2nd
    championship_matches = Match.query.filter_by(
        tournament_id=tournament_id,
        round_type='Championship',
        match_status='Completed'
    ).order_by(Match.round_number.desc()).all()

    if championship_matches:
        final_match = championship_matches[0]

        # Determine winner and runner-up from final championship match
        if final_match.team1_score > final_match.team2_score:
            winner_team_id = final_match.team1_id
            runner_up_team_id = final_match.team2_id
        else:
            winner_team_id = final_match.team2_id
            runner_up_team_id = final_match.team1_id

        # Set final places
        winner_team = Team.query.filter_by(tournament_id=tournament_id, team_id=winner_team_id).first()
        runner_up_team = Team.query.filter_by(tournament_id=tournament_id, team_id=runner_up_team_id).first()

        if winner_team:
            winner_team.final_place = 1
        if runner_up_team:
            runner_up_team.final_place = 2

    # Calculate places for eliminated teams based on elimination order
    _calculate_elimination_places(tournament_id)


def _calculate_elimination_places(tournament_id):
    """Calculate final places for teams based on when they were eliminated"""
    # Get all matches in reverse order (latest eliminations first)
    matches = Match.query.filter_by(tournament_id=tournament_id, match_status='Completed').order_by(Match.match_order.desc()).all()

    current_place = 3  # Start with 3rd place (1st and 2nd set by championship)

    for match in matches:
        # Skip championship matches (already handled)
        if match.round_type == 'Championship':
            continue

        # Find the losing team
        if match.team1_score < match.team2_score:
            losing_team_id = match.team1_id
        else:
            losing_team_id = match.team2_id

        # Set final place if not already set
        losing_team = Team.query.filter_by(tournament_id=tournament_id, team_id=losing_team_id).first()
        if losing_team and not losing_team.final_place:
            losing_team.final_place = current_place
            current_place += 1


def _update_teammate_history(tournament_id):
    """Update teammate history for all teams in completed tournament"""
    teams = Team.query.filter_by(tournament_id=tournament_id).all()

    for team in teams:
        if not team.is_ghost_team and team.player2_id and team.final_place:
            # Update history for both players
            for player_id, teammate_id in [(team.player1_id, team.player2_id), (team.player2_id, team.player1_id)]:
                history = TeamHistory.query.filter_by(player_id=player_id, teammate_id=teammate_id).first()

                if history:
                    # Calculate new average place
                    total_place = (history.average_place or 0) * history.times_paired + team.final_place
                    history.times_paired += 1
                    history.average_place = total_place / history.times_paired
                else:
                    history = TeamHistory(
                        player_id=player_id,
                        teammate_id=teammate_id,
                        times_paired=1,
                        average_place=team.final_place
                    )
                    db.session.add(history)


def _update_seasonal_points(tournament_id):
    """Update seasonal points for all teams and players in tournament"""
    teams = Team.query.filter_by(tournament_id=tournament_id).all()

    for team in teams:
        # Calculate team points: 1 for participation + match wins + top 4 bonus + undefeated bonus
        participation_points = 1
        match_wins = _count_team_match_wins(tournament_id, team.team_id)
        top_4_bonus = 2 if team.final_place and team.final_place <= 4 else 0
        undefeated_bonus = 3 if _is_team_undefeated(tournament_id, team.team_id) else 0

        team.points_earned = participation_points + match_wins + top_4_bonus + undefeated_bonus

        # Update player seasonal points
        if team.player1_id:
            player1 = RegisteredPlayer.query.get(team.player1_id)
            if player1:
                player1.seasonal_points += team.points_earned

        if team.player2_id:
            player2 = RegisteredPlayer.query.get(team.player2_id)
            if player2:
                player2.seasonal_points += team.points_earned


def _calculate_payouts(total_payout_pot, payout_config):
    """Return (first_place_payout, second_place_payout) given pot and config."""
    if payout_config and payout_config.get('mode') == 'percentage':
        second_pct = float(payout_config.get('second_place_value', 30)) / 100.0
        second_place_payout = total_payout_pot * second_pct
        first_place_payout = total_payout_pot - second_place_payout
    elif payout_config and payout_config.get('mode') == 'fixed':
        second_place_payout = float(payout_config.get('second_place_value', 0))
        first_place_payout = total_payout_pot - second_place_payout
    else:
        # Legacy hardcoded formula
        if total_payout_pot <= 60:
            second_place_payout = 20
        else:
            second_place_payout = min(40, total_payout_pot - 40) if total_payout_pot > 40 else 0
        first_place_payout = total_payout_pot - second_place_payout

    # 1st place must never receive less than 2nd place
    if first_place_payout < second_place_payout:
        first_place_payout, second_place_payout = second_place_payout, first_place_payout

    return Decimal(first_place_payout), second_place_payout


def _distribute_cash_payouts(tournament_id):
    """Calculate and distribute cash payouts to players"""
    tournament = Tournament.query.get(tournament_id)
    registrations = TournamentRegistration.query.filter_by(tournament_id=tournament_id).all()
    total_participants = len(registrations)

    buy_in = float(tournament.buy_in_per_player) if tournament and tournament.buy_in_per_player is not None else 5.0
    total_payout_pot = buy_in * total_participants
    payout_config = tournament.payout_config if tournament else None

    # Get total ace pot balance across all tournaments
    ace_pot_balance = db.session.query(db.func.sum(AcePot.amount)).scalar() or 0

    # Find 1st and 2nd place teams
    first_place_team = Team.query.filter_by(tournament_id=tournament_id, final_place=1).first()
    second_place_team = Team.query.filter_by(tournament_id=tournament_id, final_place=2).first()  # noqa: F841

    first_place_payout, second_place_payout = _calculate_payouts(total_payout_pot, payout_config)

    # Check if first place went undefeated for ace pot
    ace_pot_payout = 0
    if first_place_team and _team_is_undefeated(tournament_id, first_place_team.team_id):
        ace_pot_payout = ace_pot_balance
        first_place_payout += ace_pot_payout

        # Update ace pot tracker
        if ace_pot_payout > 0:
            player1 = RegisteredPlayer.query.get(first_place_team.player1_id)
            player2 = RegisteredPlayer.query.get(first_place_team.player2_id) if first_place_team.player2_id else None

            if player2 and not first_place_team.is_ghost_team:
                team_names = f"{player1.player_name} & {player2.player_name}"
            else:
                team_names = player1.player_name

            payout_entry = AcePot(
                tournament_id=tournament_id,
                date=db.func.current_date(),
                description=f'Ace pot payout to {team_names}',
                amount=-ace_pot_payout
            )
            db.session.add(payout_entry)

    # Update tournament with ace pot payout amount
    if tournament:
        tournament.ace_pot_payout = ace_pot_payout

    # Distribute cash to players
    for reg in registrations:
        player = RegisteredPlayer.query.get(reg.player_id)
        if player:
            player_team = Team.query.filter_by(tournament_id=tournament_id).filter(
                db.or_(Team.player1_id == reg.player_id, Team.player2_id == reg.player_id)
            ).first()

            if player_team:
                teammates_count = 2 if player_team.player2_id and not player_team.is_ghost_team else 1

                if player_team.final_place == 1:
                    player.seasonal_cash += Decimal(str(first_place_payout / teammates_count))
                elif player_team.final_place == 2:
                    player.seasonal_cash += Decimal(str(second_place_payout / teammates_count))

    # Save final payout amounts to current tournament
    tournament.first_payout = first_place_payout
    tournament.second_payout = second_place_payout
    db.session.commit()


def _count_team_match_wins(tournament_id, team_id):
    """Count matches won by specific team (excluding byes)"""
    matches = Match.query.filter_by(tournament_id=tournament_id).filter(
        db.or_(Match.team1_id == team_id, Match.team2_id == team_id)
    ).filter(Match.match_status == 'Completed').all()

    wins = 0
    for match in matches:
        # Skip bye matches (only one team)
        if match.team2_id is None:
            continue

        if ((match.team1_id == team_id and match.team1_score > match.team2_score) or
                (match.team2_id == team_id and match.team2_score > match.team1_score)):
            wins += 1

    return wins


def _is_team_undefeated(tournament_id, team_id):
    """Check if specific team went undefeated"""
    matches = Match.query.filter_by(tournament_id=tournament_id).filter(
        db.or_(Match.team1_id == team_id, Match.team2_id == team_id)
    ).filter(Match.match_status == 'Completed').all()

    for match in matches:
        # Skip bye matches
        if match.team2_id is None:
            continue

        # If team lost any match, not undefeated
        if ((match.team1_id == team_id and match.team1_score < match.team2_score) or
                (match.team2_id == team_id and match.team2_score < match.team1_score)):
            return False

    return True


def _team_is_undefeated(tournament_id, team_id):
    """Check if specific team went undefeated"""
    matches = Match.query.filter_by(tournament_id=tournament_id).filter(
        db.or_(Match.team1_id == team_id, Match.team2_id == team_id)
    ).filter(Match.match_status == 'Completed').all()

    for match in matches:
        # If team lost any match, not undefeated
        if ((match.team1_id == team_id and match.team1_score < match.team2_score) or
                (match.team2_id == team_id and match.team2_score < match.team1_score)):
            return False

    return True


@matches_bp.route('/tournaments/<int:tournament_id>/create-championship', methods=['POST'])
@require_role(app='putt', role='director')
def create_championship_round(tournament_id):
    tournament = Tournament.query.get(tournament_id)
    if not tournament:
        return jsonify({'error': 'Tournament not found'}), 404

    # Get the highest match_id to continue numbering
    last_match = Match.query.filter_by(tournament_id=tournament_id).order_by(Match.match_id.desc()).first()
    next_match_id = (last_match.match_id + 1) if last_match else 1

    # Create Championship Match 1 (WB winner vs LB winner)
    championship_1 = Match(
        tournament_id=tournament_id,
        match_id=next_match_id,
        stage_type='Finals',
        round_type='Championship',
        round_number=0,
        position_in_round=0,
        stage_match_number=next_match_id,
        match_order=next_match_id,
        match_status='Pending'
    )

    # Find and seed the survivors
    wb_final = Match.query.filter_by(tournament_id=tournament_id, round_type='Winners').order_by(Match.round_number.desc()).first()
    lb_final = Match.query.filter_by(tournament_id=tournament_id, round_type='Losers').order_by(Match.round_number.desc()).first()

    if wb_final and wb_final.match_status == 'Completed':
        wb_winner = wb_final.team1_id if wb_final.team1_score > wb_final.team2_score else wb_final.team2_id
        championship_1.team1_id = wb_winner

    if lb_final and lb_final.match_status == 'Completed':
        lb_winner = lb_final.team1_id if lb_final.team1_score > lb_final.team2_score else lb_final.team2_id
        championship_1.team2_id = lb_winner

    # If both teams are seeded, make it schedulable
    if championship_1.team1_id and championship_1.team2_id:
        championship_1.match_status = 'Scheduled'

    db.session.add(championship_1)
    db.session.commit()

    return jsonify({
        'tournament_id': tournament_id,
        'championship_match_1': championship_1.match_id,
        'message': 'Championship match created'
    }), 201
