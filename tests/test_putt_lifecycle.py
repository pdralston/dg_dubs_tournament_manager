"""
DG-Putt API tests (Phase 2 fold-in).

Exercises the consolidated /api/putt/* blueprints against the org-aware auth
model: public reads need no auth, writes require a 'putt' director membership,
and delete/audit/archive require 'putt' admin (derived from the org owner
governance role). Uses the shared in-memory SQLite fixtures from conftest.
"""

import pytest


# ── Public reads (no auth) ──────────────────────────────────────────────────

class TestPuttPublicReads:
    def test_players_list_public(self, client):
        r = client.get('/api/putt/players')
        assert r.status_code == 200
        assert r.get_json() == []

    def test_tournaments_list_public(self, client):
        r = client.get('/api/putt/tournaments')
        assert r.status_code == 200
        assert r.get_json() == []

    def test_ace_pot_public(self, client):
        r = client.get('/api/putt/ace-pot')
        assert r.status_code == 200
        assert r.get_json() == []

    def test_seasons_public(self, client):
        r = client.get('/api/putt/seasons')
        assert r.status_code == 200
        assert r.get_json() == []


# ── Auth gating ─────────────────────────────────────────────────────────────

class TestPuttAuthGating:
    def test_create_player_unauthenticated_401(self, client):
        r = client.post('/api/putt/players', json={'player_name': 'A', 'division': 'Am'})
        assert r.status_code == 401

    def test_create_player_director_ok(self, director_client):
        r = director_client.post('/api/putt/players', json={'player_name': 'A', 'division': 'Am'})
        assert r.status_code == 201, r.get_json()

    def test_delete_tournament_director_forbidden(self, director_client):
        # delete_tournament requires putt admin; a director must be 403.
        r = director_client.delete('/api/putt/tournaments/1')
        assert r.status_code == 403

    def test_archive_preview_director_forbidden(self, director_client):
        r = director_client.get('/api/putt/archive/preview')
        assert r.status_code == 403

    def test_archive_preview_admin_ok(self, admin_client):
        r = admin_client.get('/api/putt/archive/preview')
        assert r.status_code == 200
        assert r.get_json()['can_archive'] is False  # no completed tournaments


# ── Player lifecycle ────────────────────────────────────────────────────────

class TestPuttPlayerLifecycle:
    def test_create_list_update_player(self, director_client):
        # Create
        r = director_client.post('/api/putt/players',
                                 json={'player_name': 'Alice', 'division': 'Pro', 'nickname': 'Ace'})
        assert r.status_code == 201
        created = r.get_json()['created']
        assert len(created) == 1
        pid = created[0]['player_id']

        # List reflects creation
        r = director_client.get('/api/putt/players')
        names = {p['player_name'] for p in r.get_json()}
        assert 'Alice' in names

        # Detail
        r = director_client.get(f'/api/putt/players/{pid}')
        assert r.status_code == 200
        body = r.get_json()
        assert body['division'] == 'Pro'
        assert body['nickname'] == 'Ace'

        # Update
        r = director_client.put(f'/api/putt/players/{pid}', json={'division': 'Am'})
        assert r.status_code == 200
        assert r.get_json()['division'] == 'Am'

    def test_duplicate_player_name_rejected(self, director_client):
        director_client.post('/api/putt/players', json={'player_name': 'Bob', 'division': 'Am'})
        r = director_client.post('/api/putt/players', json={'player_name': 'Bob', 'division': 'Am'})
        # All failed, none created -> 400 with errors
        assert r.status_code == 400
        assert 'errors' in r.get_json()

    def test_invalid_division_rejected(self, director_client):
        r = director_client.post('/api/putt/players',
                                 json={'player_name': 'C', 'division': 'Nope'})
        assert r.status_code == 400


# ── Tournament creation + team generation ───────────────────────────────────

class TestPuttTournamentCreation:
    def _make_players(self, director_client, n):
        ids = []
        for i in range(n):
            r = director_client.post('/api/putt/players',
                                     json={'player_name': f'P{i}', 'division': 'Am'})
            assert r.status_code == 201
            ids.append(r.get_json()['created'][0]['player_id'])
        return ids

    def test_create_tournament_generates_teams(self, director_client):
        ids = self._make_players(director_client, 4)
        r = director_client.post('/api/putt/tournaments', json={
            'tournament_date': '2026-05-01',
            'players': [{'player_id': pid, 'bought_ace_pot': False} for pid in ids],
            'ace_pot_per_player': 1.00,
            'buy_in_per_player': 5.00,
        })
        assert r.status_code == 201, r.get_json()
        body = r.get_json()
        assert body['status'] == 'Scheduled'
        # 4 players -> 2 teams
        assert body['teams_generated'] == 2
        assert body['total_teams'] == 2

    def test_create_tournament_requires_two_players(self, director_client):
        ids = self._make_players(director_client, 1)
        r = director_client.post('/api/putt/tournaments', json={
            'tournament_date': '2026-05-01',
            'players': [{'player_id': ids[0]}],
            'ace_pot_per_player': 1.00,
        })
        assert r.status_code == 400

    def test_odd_players_make_ghost_team(self, director_client):
        ids = self._make_players(director_client, 3)
        r = director_client.post('/api/putt/tournaments', json={
            'tournament_date': '2026-05-02',
            'players': [{'player_id': pid} for pid in ids],
            'ace_pot_per_player': 1.00,
        })
        assert r.status_code == 201
        # 3 players -> 1 full team + 1 ghost team = 2 teams
        assert r.get_json()['teams_generated'] == 2

    def test_pending_tournament_lifecycle(self, director_client):
        # Create a Pending tournament, add players, finalize -> Scheduled
        r = director_client.post('/api/putt/tournaments/pending',
                                 json={'tournament_date': '2026-06-01'})
        assert r.status_code == 201
        tid = r.get_json()['tournament_id']
        assert r.get_json()['status'] == 'Pending'

        ids = self._make_players(director_client, 2)
        for pid in ids:
            r = director_client.post(f'/api/putt/tournaments/{tid}/players',
                                     json={'player_id': pid})
            assert r.status_code == 201

        r = director_client.post(f'/api/putt/tournaments/{tid}/finalize', json={})
        assert r.status_code == 200
        assert r.get_json()['status'] == 'Scheduled'


# ── Org scoping sanity ──────────────────────────────────────────────────────

class TestPuttOrgScoping:
    def test_created_player_is_org_stamped(self, director_client, app, db):
        r = director_client.post('/api/putt/players',
                                 json={'player_name': 'Scoped', 'division': 'Am'})
        assert r.status_code == 201
        from backend.models import PuttPlayer
        from backend.shared.org_context import DEFAULT_ORG_ID
        with app.app_context():
            p = PuttPlayer.query.filter_by(player_name='Scoped').first()
            assert p is not None
            assert p.org_id == DEFAULT_ORG_ID
