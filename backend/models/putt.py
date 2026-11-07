"""DG-Putt domain models.

Putting-league tournament manager: double-elimination brackets, real-time
match updates, season tracking.

Folded in from the standalone DG-Putt repo (Phase 2 consolidation). All tables
are renamed ``putt_*`` to avoid collisions with the DG-Dubs domain tables of
the same name (``tournaments``, ``teams``, ``seasons``) — these are genuinely
different domains and are not shared. DG-Putt's standalone ``users`` table is
NOT folded in here: identity + authz use the shared ``users`` +
``org_memberships`` / ``org_roles`` model.

Every tenant-owned table carries ``org_id`` via ``TenantMixin``; the scoping
layer stamps it on write. Enum type names are namespaced ``putt_*`` so they do
not clash with the Dubs/Tags enum types in the shared schema.
"""

from datetime import datetime
from .platform import db, TenantMixin


class PuttSeason(TenantMixin, db.Model):
    """Archived-season record. A tournament with NULL season_id is current."""
    __tablename__ = 'putt_seasons'

    season_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    season_name = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    archived_at = db.Column(db.DateTime, default=datetime.utcnow)


class PuttPlayer(TenantMixin, db.Model):
    """Player registry (was ``registered_players``)."""
    __tablename__ = 'putt_players'

    player_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    player_name = db.Column(db.String(100), nullable=False)
    nickname = db.Column(db.String(50), nullable=True)
    division = db.Column(
        db.Enum('Pro', 'Am', 'Junior', name='putt_division_enum'),
        nullable=False,
    )
    seasonal_points = db.Column(db.Integer, default=0)
    seasonal_cash = db.Column(db.Numeric(10, 2), default=0.00)
    lifetime_earnings = db.Column(db.Numeric(10, 2), default=0.00)
    lifetime_ace_pots = db.Column(db.Integer, default=0)
    events_participated = db.Column(db.Integer, default=0)
    seasonal_wins = db.Column(db.Integer, default=0)
    average_place = db.Column(db.Numeric(4, 2), nullable=True)

    __table_args__ = (
        db.UniqueConstraint('org_id', 'player_name', name='uq_putt_players_org_name'),
    )


class PuttTournament(TenantMixin, db.Model):
    """Tournament/event record (was ``tournaments``)."""
    __tablename__ = 'putt_tournaments'

    tournament_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    tournament_date = db.Column(db.Date, nullable=False)
    status = db.Column(
        db.Enum(
            'Pending', 'Scheduled', 'In_Progress', 'Completed', 'Cancelled',
            name='putt_tournament_status_enum',
        ),
        default='Scheduled',
    )
    total_teams = db.Column(db.Integer)
    ace_pot_payout = db.Column(db.Numeric(10, 2), default=0.00)
    stations = db.Column(db.Integer, default=6)
    buy_in_per_player = db.Column(db.Numeric(10, 2), default=5.00)
    payout_config = db.Column(db.JSON, nullable=True)
    first_payout = db.Column(db.Numeric(10, 2), default=0.00)
    second_payout = db.Column(db.Numeric(10, 2), default=0.00)
    season_id = db.Column(
        db.Integer, db.ForeignKey('putt_seasons.season_id'), nullable=True,
    )


class PuttRegistration(TenantMixin, db.Model):
    """Player <-> tournament registration (was ``tournament_registrations``)."""
    __tablename__ = 'putt_registrations'

    tournament_id = db.Column(
        db.Integer, db.ForeignKey('putt_tournaments.tournament_id'), primary_key=True,
    )
    player_id = db.Column(
        db.Integer, db.ForeignKey('putt_players.player_id'), primary_key=True,
    )
    bought_ace_pot = db.Column(db.Boolean, default=False)


class PuttTeamHistory(TenantMixin, db.Model):
    """Teammate pairing stats (was ``team_history``)."""
    __tablename__ = 'putt_team_history'

    player_id = db.Column(
        db.Integer, db.ForeignKey('putt_players.player_id'), primary_key=True,
    )
    teammate_id = db.Column(
        db.Integer, db.ForeignKey('putt_players.player_id'), primary_key=True,
    )
    times_paired = db.Column(db.Integer, default=0)
    average_place = db.Column(db.Numeric(4, 2))


class PuttSeasonStanding(TenantMixin, db.Model):
    """Legacy historical standings (was ``season_standings``). Retained but no
    longer the archive mechanism (the season_id-FK model superseded it)."""
    __tablename__ = 'putt_season_standings'

    player_id = db.Column(
        db.Integer, db.ForeignKey('putt_players.player_id'), primary_key=True,
    )
    season_year = db.Column(db.Integer, primary_key=True)
    division = db.Column(
        db.Enum('Pro', 'Am', 'Junior', name='putt_division_enum'),
        nullable=False,
    )
    final_place = db.Column(db.Integer)


class PuttAcePot(TenantMixin, db.Model):
    """Ace-pot transaction history (was ``ace_pot``)."""
    __tablename__ = 'putt_ace_pot'

    ace_pot_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    tournament_id = db.Column(
        db.Integer, db.ForeignKey('putt_tournaments.tournament_id'), nullable=True,
    )
    date = db.Column(db.Date, nullable=False)
    description = db.Column(db.String(255), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)


class PuttTeam(TenantMixin, db.Model):
    """Team composition (was ``teams``)."""
    __tablename__ = 'putt_teams'

    team_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    tournament_id = db.Column(
        db.Integer, db.ForeignKey('putt_tournaments.tournament_id'), nullable=False,
    )
    player1_id = db.Column(
        db.Integer, db.ForeignKey('putt_players.player_id'), nullable=False,
    )
    player2_id = db.Column(
        db.Integer, db.ForeignKey('putt_players.player_id'), nullable=True,
    )
    is_ghost_team = db.Column(db.Boolean, default=False)
    seed_number = db.Column(db.Integer)
    final_place = db.Column(db.Integer)
    points_earned = db.Column(db.Integer)


class PuttMatch(TenantMixin, db.Model):
    """Double-elim match (was ``matches``). Composite PK (tournament_id,
    match_id) preserved."""
    __tablename__ = 'putt_matches'

    tournament_id = db.Column(
        db.Integer, db.ForeignKey('putt_tournaments.tournament_id'), primary_key=True,
    )
    match_id = db.Column(db.Integer, primary_key=True)
    stage_type = db.Column(
        db.Enum('Group_A', 'Group_B', 'Finals', name='putt_stage_type_enum'),
        nullable=False,
    )
    round_type = db.Column(
        db.Enum('Winners', 'Losers', 'Championship', name='putt_round_type_enum'),
        nullable=False,
    )
    round_number = db.Column(db.Integer, nullable=False)
    position_in_round = db.Column(db.Integer, nullable=False)
    stage_match_number = db.Column(db.Integer, nullable=False)
    match_order = db.Column(db.Integer, nullable=False)
    team1_id = db.Column(db.Integer, db.ForeignKey('putt_teams.team_id'), nullable=True)
    team2_id = db.Column(db.Integer, db.ForeignKey('putt_teams.team_id'), nullable=True)
    team1_score = db.Column(db.Integer)
    team2_score = db.Column(db.Integer)
    station_assignment = db.Column(db.Integer)
    match_status = db.Column(
        db.Enum(
            'Scheduled', 'In_Progress', 'Completed', 'Pending',
            name='putt_match_status_enum',
        ),
        default='Pending',
    )
    winner_advances_to_match_id = db.Column(db.Integer, nullable=True)
    loser_advances_to_match_id = db.Column(db.Integer, nullable=True)
