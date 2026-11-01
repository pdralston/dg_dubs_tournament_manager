"""Regression tests for DG-Dubs season archiving.

Season archiving (`POST /api/archive`) is a complex, destructive, multi-step
operation that is critical to app function. In one transaction it:

  1. Creates a ``Season`` spanning the completed, unarchived tournaments.
  2. Stamps those tournaments with the new ``season_id``.
  3. Purges players that have no rating history (orphans).
  4. Rolls ``seasonal_cash`` into ``lifetime_cash`` and zeroes seasonal.
  5. Zeroes ``tournaments_played`` for the new season.
  6. Normalizes surviving player ratings into the 900..1400 band.
  7. Resets the ace-pot ledger, carrying the prior balance into a single new
     ``ace_pot_tracker`` row.

Step 7 is where a multi-org regression bit us: the carry-over row is written
with raw SQL, which bypasses the ``before_flush`` hook that stamps ``org_id``
on ORM writes. Without an explicit ``org_id`` the insert violated
``fk_ace_pot_tracker_org_id``. ``test_carryover_row_has_org_id`` and
``test_archive_succeeds_with_ace_pot_balance`` lock that fix in place; the rest
guard the surrounding behavior so future refactors of this critical path are
caught.

Data is seeded directly through the ORM inside an app context so the org
stamping hook runs (mirroring real request writes), then the in-memory rating
system is reloaded so API-level reads reflect the seeded state.
"""

import pytest

from datetime import date

from backend.models import (
    db as _db,
    Player,
    Tournament,
    PlayerHistory,
    AcePotTracker,
    Season,
)
from backend.shared.org_context import DEFAULT_ORG_ID


EVENT_DATE = date(2026, 6, 15)


def _seed_season(app, *, ace_pot_balance=16.0, with_orphan=True):
    """Seed a completed-but-unarchived season's worth of data.

    Returns a dict describing what was seeded so tests can assert against it.

    Two players (Alice, Bob) each have a PlayerHistory row (so they survive the
    orphan purge). Optionally a third player (Carol) with no history is seeded
    to exercise the purge. One completed tournament ties the history together.
    An ace-pot ledger with the given net balance is seeded.

    Seeding runs inside a ``test_request_context`` so the ``before_flush`` org
    stamping hook fires (it intentionally no-ops outside a request), exactly as
    a real write would.
    """
    with app.test_request_context():
        alice = Player(name='Alice', rating=1200, tournaments_played=3,
                       seasonal_cash=50, lifetime_cash=100)
        bob = Player(name='Bob', rating=1000, tournaments_played=3,
                     seasonal_cash=20, lifetime_cash=0)
        _db.session.add_all([alice, bob])
        if with_orphan:
            carol = Player(name='Carol', rating=1100, tournaments_played=0,
                           seasonal_cash=0, lifetime_cash=0)
            _db.session.add(carol)
        _db.session.flush()

        tourney = Tournament(date=EVENT_DATE, course='Test Course',
                             team_count=1, status='Completed')
        _db.session.add(tourney)
        _db.session.flush()

        _db.session.add_all([
            PlayerHistory(player_id=alice.player_id, tournament_id=tourney.tournament_id,
                          old_rating=1180, new_rating=1200, position=1,
                          expected_position=1.5, score=50, with_ghost=False),
            PlayerHistory(player_id=bob.player_id, tournament_id=tourney.tournament_id,
                          old_rating=1010, new_rating=1000, position=2,
                          expected_position=1.5, score=55, with_ghost=False),
        ])

        # Ace-pot ledger: a couple of entries summing to the target balance.
        if ace_pot_balance:
            _db.session.add_all([
                AcePotTracker(date=EVENT_DATE, description='Buy-ins', amount=10.0,
                              balance=10.0, tournament_id=tourney.tournament_id),
                AcePotTracker(date=EVENT_DATE, description='More buy-ins',
                              amount=ace_pot_balance - 10.0, balance=ace_pot_balance,
                              tournament_id=tourney.tournament_id),
            ])
        _db.session.commit()

        seeded = {
            'tournament_id': tourney.tournament_id,
            'alice_id': alice.player_id,
            'bob_id': bob.player_id,
            'ace_pot_balance': ace_pot_balance,
        }

    # Reflect the seeded state in the in-memory rating system used by GET routes.
    with app.app_context():
        app.rating_system.load_data()
    return seeded


class TestArchiveAcePotCarryover:
    """The specific FK regression: carry-over insert must set org_id."""

    def test_archive_succeeds_with_ace_pot_balance(self, app, admin_client):
        """End-to-end: archiving with a non-zero ace pot must not 500.

        This is the direct regression for the IntegrityError on
        fk_ace_pot_tracker_org_id.
        """
        _seed_season(app, ace_pot_balance=16.0)

        resp = admin_client.post('/api/archive', json={'season_name': '2026'})

        assert resp.status_code == 200, resp.json
        assert 'archived successfully' in resp.json['message']

    def test_carryover_row_has_org_id(self, app, admin_client):
        """The single carry-over row must exist with the correct org_id and
        a balance equal to the prior ledger sum."""
        seeded = _seed_season(app, ace_pot_balance=16.0)

        resp = admin_client.post('/api/archive', json={'season_name': '2026'})
        assert resp.status_code == 200, resp.json

        with app.app_context():
            rows = AcePotTracker.query.all()
            assert len(rows) == 1, 'ledger should be reset to a single carry-over row'
            carry = rows[0]
            assert carry.org_id == DEFAULT_ORG_ID
            assert float(carry.amount) == pytest.approx(seeded['ace_pot_balance'])
            assert float(carry.balance) == pytest.approx(seeded['ace_pot_balance'])
            assert carry.description == 'Carry-over from 2026'

    def test_zero_balance_writes_no_carryover_row(self, app, admin_client):
        """When the ace pot is empty, archiving clears the ledger and writes
        no carry-over row."""
        _seed_season(app, ace_pot_balance=0.0)

        resp = admin_client.post('/api/archive', json={'season_name': '2026'})
        assert resp.status_code == 200, resp.json

        with app.app_context():
            assert AcePotTracker.query.count() == 0


class TestArchiveSeasonAndTournaments:
    def test_season_created_and_tournaments_assigned(self, app, admin_client):
        seeded = _seed_season(app)

        resp = admin_client.post('/api/archive', json={'season_name': '2026'})
        assert resp.status_code == 200, resp.json

        with app.app_context():
            season = Season.query.filter_by(season_name='2026').one()
            assert season.org_id == DEFAULT_ORG_ID
            t = Tournament.query.get(seeded['tournament_id'])
            assert t.season_id == season.season_id
            # No completed, unarchived tournaments remain.
            assert Tournament.query.filter_by(season_id=None).filter(
                Tournament.status == 'Completed'
            ).count() == 0

    def test_requires_season_name(self, app, admin_client):
        _seed_season(app)
        resp = admin_client.post('/api/archive', json={'season_name': '   '})
        assert resp.status_code == 400
        assert 'required' in resp.json['error'].lower()

    def test_no_completed_tournaments_rejected(self, app, admin_client):
        # Seed nothing archivable.
        resp = admin_client.post('/api/archive', json={'season_name': '2026'})
        assert resp.status_code == 400
        assert 'no completed tournaments' in resp.json['error'].lower()


class TestArchivePlayerEffects:
    def test_orphan_players_purged_survivors_kept(self, app, admin_client):
        _seed_season(app, with_orphan=True)

        resp = admin_client.post('/api/archive', json={'season_name': '2026'})
        assert resp.status_code == 200, resp.json

        with app.app_context():
            names = {p.name for p in Player.query.all()}
            assert 'Alice' in names and 'Bob' in names
            assert 'Carol' not in names, 'player with no history should be purged'

    def test_seasonal_cash_rolled_into_lifetime(self, app, admin_client):
        _seed_season(app)

        resp = admin_client.post('/api/archive', json={'season_name': '2026'})
        assert resp.status_code == 200, resp.json

        with app.app_context():
            alice = Player.query.filter_by(name='Alice').one()
            # Alice started with lifetime=100, seasonal=50.
            assert float(alice.lifetime_cash) == pytest.approx(150.0)
            assert float(alice.seasonal_cash) == pytest.approx(0.0)

    def test_tournaments_played_zeroed(self, app, admin_client):
        _seed_season(app)

        resp = admin_client.post('/api/archive', json={'season_name': '2026'})
        assert resp.status_code == 200, resp.json

        with app.app_context():
            for p in Player.query.all():
                assert p.tournaments_played == 0

    def test_ratings_normalized_into_band(self, app, admin_client):
        _seed_season(app)

        resp = admin_client.post('/api/archive', json={'season_name': '2026'})
        assert resp.status_code == 200, resp.json

        with app.app_context():
            ratings = sorted(float(p.rating) for p in Player.query.all())
            # Two survivors spread across the normalization band.
            assert ratings[0] == pytest.approx(900.0)
            assert ratings[-1] == pytest.approx(1400.0)
            for r in ratings:
                assert 900.0 <= r <= 1400.0


class TestArchiveAuthorization:
    def test_archive_requires_admin(self, app, director_client):
        _seed_season(app)
        resp = director_client.post('/api/archive', json={'season_name': '2026'})
        assert resp.status_code in (401, 403), resp.json

    def test_archive_requires_auth(self, app, client):
        _seed_season(app)
        resp = client.post('/api/archive', json={'season_name': '2026'})
        assert resp.status_code in (401, 403)

    def test_preview_requires_admin(self, app, director_client):
        _seed_season(app)
        resp = director_client.get('/api/archive/preview')
        assert resp.status_code in (401, 403)


class TestArchivePreview:
    def test_preview_reports_counts(self, app, admin_client):
        seeded = _seed_season(app)
        resp = admin_client.get('/api/archive/preview')
        assert resp.status_code == 200, resp.json
        body = resp.json
        assert body['event_count'] == 1
        assert body['unique_participants'] == 2
        assert body['total_participants'] == 2
        assert body['start_date'] == '2026-06-15'
        assert body['end_date'] == '2026-06-15'

    def test_preview_empty_when_nothing_to_archive(self, app, admin_client):
        resp = admin_client.get('/api/archive/preview')
        assert resp.status_code == 200, resp.json
        assert resp.json['event_count'] == 0
