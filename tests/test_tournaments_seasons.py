"""Tests for season selection in the DG-Dubs tournament directory.

Covers the feature that lets users browse previous seasons' tournaments:

  * ``GET /api/tournaments/seasons`` lists Current Season + archived seasons.
  * ``GET /api/tournaments?season_id=<id>`` returns that season's tournaments,
    with results built from persisted ``Team`` rows (archived tournaments are
    not in the in-memory rating system, which only tracks the current season).
  * ``GET /api/tournaments?season_id`` absent/null returns current-season
    (``season_id IS NULL``) tournaments.
  * ``GET /api/tournaments/<tid>`` for an archived tournament builds its
    results from ``Team`` rows.

Data is seeded through the ORM inside a request context so the ``before_flush``
org-stamping hook runs, then the in-memory rating system is reloaded so
current-season reads reflect the seeded state (mirroring test_archive.py).
"""

from datetime import date

import pytest

from backend.models import (
    db as _db,
    Player,
    Tournament,
    Team,
    Season,
)


CURRENT_DATE = date(2026, 7, 1)
ARCHIVED_DATE = date(2025, 6, 1)


def _seed(app):
    """Seed one archived season (with a completed tournament + Team rows) and
    one current-season completed tournament.

    Returns a dict of the created ids for assertions.
    """
    with app.test_request_context():
        alice = Player(name='Alice', rating=1200, tournaments_played=1,
                       seasonal_cash=0, lifetime_cash=0)
        bob = Player(name='Bob', rating=1000, tournaments_played=1,
                     seasonal_cash=0, lifetime_cash=0)
        carol = Player(name='Carol', rating=1100, tournaments_played=1,
                       seasonal_cash=0, lifetime_cash=0)
        dave = Player(name='Dave', rating=1050, tournaments_played=1,
                      seasonal_cash=0, lifetime_cash=0)
        _db.session.add_all([alice, bob, carol, dave])
        _db.session.flush()

        # Archived season spanning last year.
        season = Season(season_name='2025', start_date=date(2025, 1, 1),
                        end_date=date(2025, 12, 31))
        _db.session.add(season)
        _db.session.flush()

        # Archived tournament belonging to that season, with recorded teams.
        archived = Tournament(date=ARCHIVED_DATE, course='Old Course',
                              team_count=2, status='Completed',
                              season_id=season.season_id)
        _db.session.add(archived)
        _db.session.flush()

        _db.session.add_all([
            Team(tournament_id=archived.tournament_id,
                 player1_id=alice.player_id, player2_id=bob.player_id,
                 position=1, expected_position=1.5, score=48,
                 team_rating=1100, payout=60.0),
            Team(tournament_id=archived.tournament_id,
                 player1_id=carol.player_id, player2_id=dave.player_id,
                 position=2, expected_position=1.5, score=52,
                 team_rating=1075, payout=0.0),
        ])

        # Current-season completed tournament (season_id NULL).
        current = Tournament(date=CURRENT_DATE, course='New Course',
                             team_count=1, status='Completed')
        _db.session.add(current)
        _db.session.flush()

        _db.session.commit()

        seeded = {
            'season_id': season.season_id,
            'archived_tid': archived.tournament_id,
            'current_tid': current.tournament_id,
        }

    with app.app_context():
        app.rating_system.load_data()
    return seeded


class TestTournamentSeasonsEndpoint:
    def test_lists_current_plus_archived(self, app, client):
        seeded = _seed(app)
        resp = client.get('/api/tournaments/seasons')
        assert resp.status_code == 200, resp.json
        seasons = resp.json
        # First entry is always the current season sentinel.
        assert seasons[0] == {'id': None, 'name': 'Current Season'}
        archived = [s for s in seasons if s['id'] is not None]
        assert any(s['id'] == seeded['season_id'] and s['name'] == '2025'
                   for s in archived)

    def test_public_access(self, app, client):
        """Seasons list is public (no auth gate)."""
        _seed(app)
        assert client.get('/api/tournaments/seasons').status_code == 200


class TestTournamentListBySeason:
    def test_current_season_default(self, app, client):
        seeded = _seed(app)
        resp = client.get('/api/tournaments')
        assert resp.status_code == 200, resp.json
        tids = {t['tournament_id'] for t in resp.json}
        assert seeded['current_tid'] in tids
        assert seeded['archived_tid'] not in tids

    def test_archived_season_filter(self, app, client):
        seeded = _seed(app)
        resp = client.get(f"/api/tournaments?season_id={seeded['season_id']}")
        assert resp.status_code == 200, resp.json
        tids = {t['tournament_id'] for t in resp.json}
        assert seeded['archived_tid'] in tids
        assert seeded['current_tid'] not in tids

    def test_archived_list_results_from_team_rows(self, app, client):
        """Archived tournaments are not in memory; their list results must be
        reconstructed from persisted Team rows."""
        seeded = _seed(app)
        resp = client.get(f"/api/tournaments?season_id={seeded['season_id']}")
        assert resp.status_code == 200, resp.json
        archived = next(t for t in resp.json
                        if t['tournament_id'] == seeded['archived_tid'])
        results = archived['results']
        assert len(results) == 2
        winner = next(r for r in results if r['position'] == 1)
        assert winner['team'] == ['Alice', 'Bob']
        assert winner['score'] == 48
        assert winner['payout'] == pytest.approx(60.0)

    def test_invalid_season_id(self, app, client):
        _seed(app)
        resp = client.get('/api/tournaments?season_id=notanumber')
        assert resp.status_code == 400


class TestArchivedTournamentDetail:
    def test_detail_results_from_team_rows(self, app, client):
        seeded = _seed(app)
        resp = client.get(f"/api/tournaments/{seeded['archived_tid']}")
        assert resp.status_code == 200, resp.json
        data = resp.json
        assert data['status'] == 'Completed'
        assert len(data['results']) == 2
        positions = sorted(r['position'] for r in data['results'])
        assert positions == [1, 2]
        loser = next(r for r in data['results'] if r['position'] == 2)
        assert loser['team'] == ['Carol', 'Dave']
        assert loser['score'] == 52
