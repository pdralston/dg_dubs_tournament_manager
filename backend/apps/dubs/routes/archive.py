"""API endpoints for season archive."""

from flask import Blueprint, jsonify, request, current_app
from backend.models import (
    db, Player, Tournament, Team, Season, PlayerHistory,
    TournamentParticipant, AcePotTracker,
)
from backend.shared.auth import admin_required
from sqlalchemy import func
from datetime import datetime

archive_bp = Blueprint('archive_api', __name__)


@archive_bp.route('/api/archive/preview', methods=['GET'])
@admin_required
def preview():
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
@admin_required
def perform_archive():
    data = request.get_json()
    season_name = data.get('season_name', '').strip() if data else ''
    if not season_name:
        return jsonify({'error': 'Season name required'}), 400

    tournaments = Tournament.query.filter_by(season_id=None).filter(
        Tournament.status == 'Completed'
    ).all()

    if not tournaments:
        return jsonify({'error': 'No completed tournaments to archive'}), 400

    dates = [t.date for t in tournaments]

    try:
        season = Season(
            season_name=season_name,
            start_date=min(dates),
            end_date=max(dates),
        )
        db.session.add(season)
        db.session.flush()

        for t in tournaments:
            t.season_id = season.season_id
        Tournament.query.filter_by(season_id=None).update({'season_id': season.season_id})

        all_players = Player.query.all()
        for p in all_players:
            has_history = PlayerHistory.query.filter_by(player_id=p.player_id).first()
            if not has_history:
                TournamentParticipant.query.filter_by(player_id=p.player_id).delete()
                db.session.delete(p)

        db.session.execute(
            db.text("UPDATE players SET lifetime_cash = lifetime_cash + seasonal_cash, seasonal_cash = 0")
        )

        db.session.execute(db.text("UPDATE players SET tournaments_played = 0"))

        remaining = Player.query.all()
        if remaining:
            ratings = [float(p.rating) for p in remaining]
            old_min, old_max = min(ratings), max(ratings)
            if old_max > old_min:
                for p in remaining:
                    normalized = 900 + (float(p.rating) - old_min) / (old_max - old_min) * 500
                    p.rating = round(normalized, 2)
            else:
                for p in remaining:
                    p.rating = 1150.00

        balance_row = db.session.execute(
            db.text("SELECT COALESCE(SUM(amount), 0) as total FROM ace_pot_tracker")
        ).fetchone()
        carry_over = float(balance_row[0]) if balance_row else 0.0

        db.session.execute(db.text("DELETE FROM ace_pot_tracker"))
        if carry_over != 0:
            db.session.execute(
                db.text("INSERT INTO ace_pot_tracker (date, description, amount, balance) VALUES (:d, :desc, :amt, :bal)"),
                {'d': datetime.now().strftime('%Y-%m-%d'), 'desc': f'Carry-over from {season_name}',
                 'amt': carry_over, 'bal': carry_over}
            )

        db.session.commit()

        rs = current_app.rating_system
        rs.load_data()

        return jsonify({'message': f'Season "{season_name}" archived successfully'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
