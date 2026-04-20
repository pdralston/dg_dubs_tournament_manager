"""API endpoints for season archive."""

from flask import Blueprint, jsonify, request, session, current_app
from tournament_core.models import db, Player, Tournament, Team, Season, PlayerHistory, \
    TournamentParticipant, AcePotTracker
from sqlalchemy import func
from datetime import datetime

archive_bp = Blueprint('archive_api', __name__)


@archive_bp.route('/api/archive/preview', methods=['GET'])
def preview():
    if session.get('role') != 'admin':
        return jsonify({'error': 'Admin required'}), 403

    # Current season = tournaments with no season_id
    tournaments = Tournament.query.filter_by(season_id=None).filter(
        Tournament.status == 'Completed'
    ).all()

    if not tournaments:
        return jsonify({
            'start_date': None, 'end_date': None,
            'event_count': 0, 'unique_participants': 0, 'total_participants': 0,
        })

    dates = [t.date for t in tournaments]
    tids = [t.tournament_id for t in tournaments]

    total_participants = PlayerHistory.query.filter(
        PlayerHistory.tournament_id.in_(tids)
    ).count()

    unique_participants = db.session.query(
        func.count(func.distinct(PlayerHistory.player_id))
    ).filter(PlayerHistory.tournament_id.in_(tids)).scalar() or 0

    return jsonify({
        'start_date': min(dates).isoformat(),
        'end_date': max(dates).isoformat(),
        'event_count': len(tournaments),
        'unique_participants': unique_participants,
        'total_participants': total_participants,
    })


@archive_bp.route('/api/archive', methods=['POST'])
def perform_archive():
    if session.get('role') != 'admin':
        return jsonify({'error': 'Admin required'}), 403

    data = request.get_json()
    season_name = data.get('season_name', '').strip() if data else ''
    if not season_name:
        return jsonify({'error': 'Season name required'}), 400

    # Current season tournaments
    tournaments = Tournament.query.filter_by(season_id=None).filter(
        Tournament.status == 'Completed'
    ).all()

    if not tournaments:
        return jsonify({'error': 'No completed tournaments to archive'}), 400

    dates = [t.date for t in tournaments]

    try:
        # 1. Create season record
        season = Season(
            season_name=season_name,
            start_date=min(dates),
            end_date=max(dates),
        )
        db.session.add(season)
        db.session.flush()  # get season_id

        # 2. Tag tournaments with season
        for t in tournaments:
            t.season_id = season.season_id
        # Also tag pending/in-progress tournaments
        Tournament.query.filter_by(season_id=None).update({'season_id': season.season_id})

        # 3. Delete players with no tournament history
        all_players = Player.query.all()
        for p in all_players:
            has_history = PlayerHistory.query.filter_by(player_id=p.player_id).first()
            if not has_history:
                TournamentParticipant.query.filter_by(player_id=p.player_id).delete()
                db.session.delete(p)

        # 4. Roll seasonal_cash into lifetime_cash, reset seasonal
        db.session.execute(
            db.text("UPDATE players SET lifetime_cash = lifetime_cash + seasonal_cash, seasonal_cash = 0")
        )

        # 5. Reset tournaments_played for the new season
        db.session.execute(db.text("UPDATE players SET tournaments_played = 0"))

        # 6. Normalize ratings (900-1400 range)
        remaining = Player.query.all()
        if remaining:
            ratings = [float(p.rating) for p in remaining]
            old_min, old_max = min(ratings), max(ratings)
            if old_max > old_min:
                for p in remaining:
                    normalized = 900 + (float(p.rating) - old_min) / (old_max - old_min) * 500
                    p.rating = round(normalized, 2)
            else:
                # All same rating — set to midpoint
                for p in remaining:
                    p.rating = 1150.00

        # 7. Collapse ace pot ledger to single carry-over entry
        balance_row = db.session.execute(
            db.text("SELECT COALESCE(SUM(amount), 0) as total FROM ace_pot_tracker")
        ).fetchone()
        carry_over = float(balance_row[0]) if balance_row else 0.0

        db.session.execute(db.text("DELETE FROM ace_pot_tracker"))
        if carry_over != 0:
            db.session.execute(
                db.text("INSERT INTO ace_pot_tracker (date, description, amount, balance) VALUES (:d, :desc, :amt, :bal)"),
                {'d': datetime.now().strftime('%Y-%m-%d'), 'desc': f'Carry-over from {season_name}', 'amt': carry_over, 'bal': carry_over}
            )

        db.session.commit()

        # 8. Reload in-memory data
        rs = current_app.rating_system
        rs.load_data()

        return jsonify({'message': f'Season "{season_name}" archived successfully'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
