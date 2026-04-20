"""SQLAlchemy models for the DG-Dubs tournament rating system."""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class Player(db.Model):
    __tablename__ = 'players'

    player_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    rating = db.Column(db.Numeric(8, 2), nullable=False, default=1000.00)
    tournaments_played = db.Column(db.Integer, nullable=False, default=0)
    is_club_member = db.Column(db.Boolean, default=False)
    seasonal_cash = db.Column(db.Numeric(8, 2), nullable=False, default=0.00)
    lifetime_cash = db.Column(db.Numeric(8, 2), nullable=False, default=0.00)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    history = db.relationship('PlayerHistory', backref='player', lazy='dynamic')
    participations = db.relationship('TournamentParticipant', backref='player', lazy='dynamic')


class Tournament(db.Model):
    __tablename__ = 'tournaments'

    tournament_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    date = db.Column(db.Date, nullable=False)
    course = db.Column(db.String(100))
    team_count = db.Column(db.Integer, nullable=False)
    status = db.Column(db.Enum('Pending', 'In Progress', 'Completed'), default='Completed')
    ace_pot_paid = db.Column(db.Boolean, default=False)
    ace_pot_paid_to = db.Column(db.String(500), nullable=True)  # comma-separated player names
    season_id = db.Column(db.Integer, db.ForeignKey('seasons.season_id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    teams = db.relationship('Team', backref='tournament', lazy='dynamic')
    participants = db.relationship('TournamentParticipant', backref='tournament', lazy='dynamic')
    ace_pot_entries = db.relationship('AcePotTracker', backref='tournament', lazy='dynamic')


class Team(db.Model):
    __tablename__ = 'teams'

    team_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournaments.tournament_id'), nullable=False)
    player1_id = db.Column(db.Integer, db.ForeignKey('players.player_id'), nullable=False)
    player2_id = db.Column(db.Integer, db.ForeignKey('players.player_id'), nullable=True)
    is_ghost_team = db.Column(db.Boolean, default=False)
    position = db.Column(db.Integer, nullable=False)
    expected_position = db.Column(db.Numeric(6, 2), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    team_rating = db.Column(db.Numeric(8, 2), nullable=False)
    payout = db.Column(db.Numeric(8, 2), nullable=False, default=0.00)

    player1 = db.relationship('Player', foreign_keys=[player1_id])
    player2 = db.relationship('Player', foreign_keys=[player2_id])


class PlayerHistory(db.Model):
    __tablename__ = 'player_history'

    history_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    player_id = db.Column(db.Integer, db.ForeignKey('players.player_id'), nullable=False)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournaments.tournament_id'), nullable=False)
    old_rating = db.Column(db.Numeric(8, 2), nullable=False)
    new_rating = db.Column(db.Numeric(8, 2), nullable=False)
    position = db.Column(db.Integer, nullable=False)
    expected_position = db.Column(db.Numeric(6, 2), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    with_ghost = db.Column(db.Boolean, nullable=False, default=False)

    tournament = db.relationship('Tournament', backref='player_histories')


class TournamentParticipant(db.Model):
    __tablename__ = 'tournament_participants'

    participant_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournaments.tournament_id'), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey('players.player_id'), nullable=False)
    ace_pot_buy_in = db.Column(db.Boolean, default=False)

    __table_args__ = (
        db.UniqueConstraint('tournament_id', 'player_id', name='uq_tournament_player'),
    )


class AcePotTracker(db.Model):
    __tablename__ = 'ace_pot_tracker'

    entry_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    date = db.Column(db.Date, nullable=False)
    description = db.Column(db.String(255), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    balance = db.Column(db.Numeric(10, 2), nullable=False)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournaments.tournament_id'), nullable=True)
    player_id = db.Column(db.Integer, db.ForeignKey('players.player_id'), nullable=True)

    player = db.relationship('Player', backref='ace_pot_entries')


class AcePotConfig(db.Model):
    __tablename__ = 'ace_pot_config'

    id = db.Column(db.Integer, primary_key=True, default=1)
    cap_amount = db.Column(db.Numeric(10, 2), nullable=False, default=100.00)


class Season(db.Model):
    __tablename__ = 'seasons'

    season_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    season_name = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    archived_at = db.Column(db.DateTime, default=datetime.utcnow)

    tournaments = db.relationship('Tournament', backref='season', lazy='dynamic')


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    salt = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default='director')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True)

    sessions = db.relationship('UserSession', backref='user', lazy='dynamic')


class UserSession(db.Model):
    __tablename__ = 'user_sessions'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    session_token = db.Column(db.String(255), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    ip_address = db.Column(db.String(50), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
