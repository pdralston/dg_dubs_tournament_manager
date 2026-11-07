"""create DG-Putt tables (org-scoped)

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-11-07

Phase 2 consolidation — fold DG-Putt into the DG-Rater schema. Creates the nine
``putt_*`` tables with ``org_id`` baked in from the start, matching the
SQLAlchemy models in ``backend/models/putt.py``.

The tables are renamed from DG-Putt's originals to avoid collisions with the
DG-Dubs domain tables of the same name (``tournaments``, ``teams``,
``seasons``):

    seasons                  -> putt_seasons
    registered_players       -> putt_players
    tournaments              -> putt_tournaments
    tournament_registrations -> putt_registrations
    team_history             -> putt_team_history
    season_standings         -> putt_season_standings
    ace_pot                  -> putt_ace_pot
    teams                    -> putt_teams
    matches                  -> putt_matches

Notes:
  * Enum TYPE names are namespaced ``putt_*`` so they don't clash with the
    Dubs/Tags enum types already in the schema.
  * ``putt_matches`` keeps its composite PK ``(tournament_id, match_id)``. The
    ``winner_advances_to_match_id`` / ``loser_advances_to_match_id`` columns are
    plain integers (no self-referential composite FK); the application manages
    these pointers. This matches the model and avoids a composite self-FK.
  * This migration CREATES EMPTY tables. Migrating the existing ``dgputt``
    schema's DATA into these tables (stamped org_id=1) is a separate one-off
    data migration run at prod cutover — not part of this schema migration.
  * Dialect: plain ``create_table`` works on both MySQL (prod) and SQLite
    (local rehearsal / pytest), so no batch/dialect branching is needed.
"""
from alembic import op
import sqlalchemy as sa


revision = 'd4e5f6a7b8c9'
down_revision = 'c3d4e5f6a7b8'
branch_labels = None
depends_on = None


def upgrade():
    # ── putt_seasons ─────────────────────────────────────────────────
    op.create_table(
        'putt_seasons',
        sa.Column('season_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('org_id', sa.Integer(), nullable=False),
        sa.Column('season_name', sa.String(length=100), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('archived_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('season_id'),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.org_id'], name='fk_putt_seasons_org_id'),
    )
    op.create_index('ix_putt_seasons_org_id', 'putt_seasons', ['org_id'])

    # ── putt_players ─────────────────────────────────────────────────
    op.create_table(
        'putt_players',
        sa.Column('player_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('org_id', sa.Integer(), nullable=False),
        sa.Column('player_name', sa.String(length=100), nullable=False),
        sa.Column('nickname', sa.String(length=50), nullable=True),
        sa.Column('division', sa.Enum('Pro', 'Am', 'Junior', name='putt_division_enum'), nullable=False),
        sa.Column('seasonal_points', sa.Integer(), nullable=True),
        sa.Column('seasonal_cash', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('lifetime_earnings', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('lifetime_ace_pots', sa.Integer(), nullable=True),
        sa.Column('events_participated', sa.Integer(), nullable=True),
        sa.Column('seasonal_wins', sa.Integer(), nullable=True),
        sa.Column('average_place', sa.Numeric(precision=4, scale=2), nullable=True),
        sa.PrimaryKeyConstraint('player_id'),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.org_id'], name='fk_putt_players_org_id'),
        sa.UniqueConstraint('org_id', 'player_name', name='uq_putt_players_org_name'),
    )
    op.create_index('ix_putt_players_org_id', 'putt_players', ['org_id'])

    # ── putt_tournaments ─────────────────────────────────────────────
    op.create_table(
        'putt_tournaments',
        sa.Column('tournament_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('org_id', sa.Integer(), nullable=False),
        sa.Column('tournament_date', sa.Date(), nullable=False),
        sa.Column(
            'status',
            sa.Enum('Pending', 'Scheduled', 'In_Progress', 'Completed', 'Cancelled',
                    name='putt_tournament_status_enum'),
            nullable=True,
        ),
        sa.Column('total_teams', sa.Integer(), nullable=True),
        sa.Column('ace_pot_payout', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('stations', sa.Integer(), nullable=True),
        sa.Column('buy_in_per_player', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('payout_config', sa.JSON(), nullable=True),
        sa.Column('first_payout', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('second_payout', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('season_id', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('tournament_id'),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.org_id'], name='fk_putt_tournaments_org_id'),
        sa.ForeignKeyConstraint(['season_id'], ['putt_seasons.season_id'], name='fk_putt_tournaments_season'),
    )
    op.create_index('ix_putt_tournaments_org_id', 'putt_tournaments', ['org_id'])
    op.create_index('ix_putt_tournaments_season', 'putt_tournaments', ['season_id'])

    # ── putt_registrations ───────────────────────────────────────────
    op.create_table(
        'putt_registrations',
        sa.Column('tournament_id', sa.Integer(), nullable=False),
        sa.Column('player_id', sa.Integer(), nullable=False),
        sa.Column('org_id', sa.Integer(), nullable=False),
        sa.Column('bought_ace_pot', sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint('tournament_id', 'player_id'),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.org_id'], name='fk_putt_registrations_org_id'),
        sa.ForeignKeyConstraint(['tournament_id'], ['putt_tournaments.tournament_id'], name='fk_putt_registrations_tournament'),
        sa.ForeignKeyConstraint(['player_id'], ['putt_players.player_id'], name='fk_putt_registrations_player'),
    )
    op.create_index('ix_putt_registrations_org_id', 'putt_registrations', ['org_id'])

    # ── putt_team_history ────────────────────────────────────────────
    op.create_table(
        'putt_team_history',
        sa.Column('player_id', sa.Integer(), nullable=False),
        sa.Column('teammate_id', sa.Integer(), nullable=False),
        sa.Column('org_id', sa.Integer(), nullable=False),
        sa.Column('times_paired', sa.Integer(), nullable=True),
        sa.Column('average_place', sa.Numeric(precision=4, scale=2), nullable=True),
        sa.PrimaryKeyConstraint('player_id', 'teammate_id'),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.org_id'], name='fk_putt_team_history_org_id'),
        sa.ForeignKeyConstraint(['player_id'], ['putt_players.player_id'], name='fk_putt_team_history_player'),
        sa.ForeignKeyConstraint(['teammate_id'], ['putt_players.player_id'], name='fk_putt_team_history_teammate'),
    )
    op.create_index('ix_putt_team_history_org_id', 'putt_team_history', ['org_id'])

    # ── putt_season_standings ────────────────────────────────────────
    op.create_table(
        'putt_season_standings',
        sa.Column('player_id', sa.Integer(), nullable=False),
        sa.Column('season_year', sa.Integer(), nullable=False),
        sa.Column('org_id', sa.Integer(), nullable=False),
        sa.Column('division', sa.Enum('Pro', 'Am', 'Junior', name='putt_division_enum'), nullable=False),
        sa.Column('final_place', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('player_id', 'season_year'),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.org_id'], name='fk_putt_season_standings_org_id'),
        sa.ForeignKeyConstraint(['player_id'], ['putt_players.player_id'], name='fk_putt_season_standings_player'),
    )
    op.create_index('ix_putt_season_standings_org_id', 'putt_season_standings', ['org_id'])

    # ── putt_ace_pot ─────────────────────────────────────────────────
    op.create_table(
        'putt_ace_pot',
        sa.Column('ace_pot_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('org_id', sa.Integer(), nullable=False),
        sa.Column('tournament_id', sa.Integer(), nullable=True),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=False),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.PrimaryKeyConstraint('ace_pot_id'),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.org_id'], name='fk_putt_ace_pot_org_id'),
        sa.ForeignKeyConstraint(['tournament_id'], ['putt_tournaments.tournament_id'], name='fk_putt_ace_pot_tournament'),
    )
    op.create_index('ix_putt_ace_pot_org_id', 'putt_ace_pot', ['org_id'])

    # ── putt_teams ───────────────────────────────────────────────────
    op.create_table(
        'putt_teams',
        sa.Column('team_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('org_id', sa.Integer(), nullable=False),
        sa.Column('tournament_id', sa.Integer(), nullable=False),
        sa.Column('player1_id', sa.Integer(), nullable=False),
        sa.Column('player2_id', sa.Integer(), nullable=True),
        sa.Column('is_ghost_team', sa.Boolean(), nullable=True),
        sa.Column('seed_number', sa.Integer(), nullable=True),
        sa.Column('final_place', sa.Integer(), nullable=True),
        sa.Column('points_earned', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('team_id'),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.org_id'], name='fk_putt_teams_org_id'),
        sa.ForeignKeyConstraint(['tournament_id'], ['putt_tournaments.tournament_id'], name='fk_putt_teams_tournament'),
        sa.ForeignKeyConstraint(['player1_id'], ['putt_players.player_id'], name='fk_putt_teams_player1'),
        sa.ForeignKeyConstraint(['player2_id'], ['putt_players.player_id'], name='fk_putt_teams_player2'),
    )
    op.create_index('ix_putt_teams_org_id', 'putt_teams', ['org_id'])

    # ── putt_matches ─────────────────────────────────────────────────
    # Composite PK (tournament_id, match_id). Advancement pointer columns are
    # plain integers (no self-referential FK) — the application manages them.
    op.create_table(
        'putt_matches',
        sa.Column('tournament_id', sa.Integer(), nullable=False),
        sa.Column('match_id', sa.Integer(), nullable=False),
        sa.Column('org_id', sa.Integer(), nullable=False),
        sa.Column('stage_type', sa.Enum('Group_A', 'Group_B', 'Finals', name='putt_stage_type_enum'), nullable=False),
        sa.Column('round_type', sa.Enum('Winners', 'Losers', 'Championship', name='putt_round_type_enum'), nullable=False),
        sa.Column('round_number', sa.Integer(), nullable=False),
        sa.Column('position_in_round', sa.Integer(), nullable=False),
        sa.Column('stage_match_number', sa.Integer(), nullable=False),
        sa.Column('match_order', sa.Integer(), nullable=False),
        sa.Column('team1_id', sa.Integer(), nullable=True),
        sa.Column('team2_id', sa.Integer(), nullable=True),
        sa.Column('team1_score', sa.Integer(), nullable=True),
        sa.Column('team2_score', sa.Integer(), nullable=True),
        sa.Column('station_assignment', sa.Integer(), nullable=True),
        sa.Column(
            'match_status',
            sa.Enum('Scheduled', 'In_Progress', 'Completed', 'Pending', name='putt_match_status_enum'),
            nullable=True,
        ),
        sa.Column('winner_advances_to_match_id', sa.Integer(), nullable=True),
        sa.Column('loser_advances_to_match_id', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('tournament_id', 'match_id'),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.org_id'], name='fk_putt_matches_org_id'),
        sa.ForeignKeyConstraint(['tournament_id'], ['putt_tournaments.tournament_id'], name='fk_putt_matches_tournament'),
        sa.ForeignKeyConstraint(['team1_id'], ['putt_teams.team_id'], name='fk_putt_matches_team1'),
        sa.ForeignKeyConstraint(['team2_id'], ['putt_teams.team_id'], name='fk_putt_matches_team2'),
    )
    op.create_index('ix_putt_matches_org_id', 'putt_matches', ['org_id'])


def downgrade():
    # FK-safe reverse order. Note: do NOT drop the ix_*_org_id indexes
    # explicitly — on MySQL those indexes back the org_id foreign key, and
    # dropping an FK-backing index while the table still exists raises error
    # 1553. ``drop_table`` removes the table together with its FKs and indexes.
    op.drop_table('putt_matches')
    op.drop_table('putt_teams')
    op.drop_table('putt_ace_pot')
    op.drop_table('putt_season_standings')
    op.drop_table('putt_team_history')
    op.drop_table('putt_registrations')
    op.drop_table('putt_tournaments')
    op.drop_table('putt_players')
    op.drop_table('putt_seasons')
