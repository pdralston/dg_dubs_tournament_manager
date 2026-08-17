"""
DG-Tags API Lifecycle Tests

Tests the full event lifecycle with the new status machine:
  Pending → Scheduled → In Progress → Complete

Covers:
  - Member management (CRUD, PII access control, search, duplicates)
  - Event creation (annual/monthly types)
  - Registration (individual, bulk CSV import)
  - Check-in workflow
  - State transitions with automated actions
  - Score submission (manual + import)
  - Tag distribution algorithm (monthly + annual, DNF handling)
  - Inventory management
  - Standings and history
"""

import io
import pytest


class TestTagMemberManagement:
    """Tests for /api/tags/members endpoints."""

    def test_create_member(self, director_client):
        resp = director_client.post('/api/tags/members', json={
            'name': 'Alice Adams',
            'udisc_name': 'alice_a',
            'current_tag': 1,
        })
        assert resp.status_code == 201
        data = resp.json
        assert data['name'] == 'Alice Adams'
        assert data['udisc_name'] == 'alice_a'
        assert data['member_id'] is not None
        assert data['current_tag'] == 1

    def test_create_member_with_pii(self, director_client):
        """Directors can submit PII during creation but it's not returned."""
        resp = director_client.post('/api/tags/members', json={
            'name': 'Bob Baker',
            'email': 'bob@example.com',
            'phone': '555-1234',
            'shipping_address': '123 Fairway Dr',
        })
        assert resp.status_code == 201
        data = resp.json
        assert 'email' not in data
        assert 'phone' not in data
        assert 'shipping_address' not in data

    def test_create_member_requires_name(self, director_client):
        resp = director_client.post('/api/tags/members', json={})
        assert resp.status_code == 400

    def test_create_member_requires_auth(self, client):
        resp = client.post('/api/tags/members', json={'name': 'Anon'})
        assert resp.status_code == 401

    def test_list_members_public(self, client, director_client):
        """Anyone can list members, but PII is excluded."""
        director_client.post('/api/tags/members', json={
            'name': 'Charlie Clark',
            'email': 'charlie@example.com',
        })
        resp = client.get('/api/tags/members')
        assert resp.status_code == 200
        members = resp.json
        assert len(members) >= 1
        for m in members:
            assert 'email' not in m
            assert 'shipping_address' not in m
            assert 'phone' not in m

    def test_list_members_admin_sees_pii(self, admin_client):
        """Admin can see PII in member list."""
        admin_client.post('/api/tags/members', json={
            'name': 'Diana Duke',
            'email': 'diana@example.com',
            'phone': '555-9999',
            'shipping_address': '456 Disc Ln',
        })
        resp = admin_client.get('/api/tags/members')
        assert resp.status_code == 200
        members = resp.json
        diana = next(m for m in members if m['name'] == 'Diana Duke')
        assert diana['email'] == 'diana@example.com'
        assert diana['phone'] == '555-9999'
        assert diana['shipping_address'] == '456 Disc Ln'

    def test_director_cannot_read_pii(self, director_client):
        """Directors can write PII but cannot read it back (write-blind)."""
        director_client.post('/api/tags/members', json={
            'name': 'Eve Evans',
            'email': 'eve@example.com',
        })
        resp = director_client.get('/api/tags/members')
        assert resp.status_code == 200
        members = resp.json
        eve = next(m for m in members if m['name'] == 'Eve Evans')
        assert 'email' not in eve

    def test_update_member(self, director_client):
        resp = director_client.post('/api/tags/members', json={'name': 'Frank'})
        mid = resp.json['member_id']

        resp = director_client.put(f'/api/tags/members/{mid}', json={
            'name': 'Frank Updated',
            'udisc_name': 'frank_u',
        })
        assert resp.status_code == 200
        assert resp.json['name'] == 'Frank Updated'

    def test_delete_member_requires_admin(self, director_client):
        resp = director_client.post('/api/tags/members', json={'name': 'Temp'})
        mid = resp.json['member_id']
        resp = director_client.delete(f'/api/tags/members/{mid}')
        assert resp.status_code == 403

    def test_delete_member_purges_pii(self, admin_client):
        resp = admin_client.post('/api/tags/members', json={
            'name': 'Gone Player',
            'email': 'gone@example.com',
        })
        mid = resp.json['member_id']
        resp = admin_client.delete(f'/api/tags/members/{mid}')
        assert resp.status_code == 200
        assert 'PII purged' in resp.json['message']

    def test_search_members(self, director_client, client):
        """Search members by name or UDisc name."""
        director_client.post('/api/tags/members', json={
            'name': 'Searchable Sam',
            'udisc_name': 'samsam',
        })
        director_client.post('/api/tags/members', json={
            'name': 'Another Person',
            'udisc_name': 'anotherperson',
        })

        resp = client.get('/api/tags/members/search?q=Sam')
        assert resp.status_code == 200
        results = resp.json
        assert len(results) >= 1
        assert any(r['name'] == 'Searchable Sam' for r in results)

    def test_search_by_udisc_name(self, director_client, client):
        director_client.post('/api/tags/members', json={
            'name': 'UDisc Player',
            'udisc_name': 'discgolf_pro',
        })
        resp = client.get('/api/tags/members/search?q=discgolf')
        assert resp.status_code == 200
        results = resp.json
        assert any(r['udisc_name'] == 'discgolf_pro' for r in results)

    def test_search_requires_min_length(self, client):
        resp = client.get('/api/tags/members/search?q=a')
        assert resp.status_code == 400

    def test_check_duplicate(self, director_client):
        """Duplicate check finds existing members."""
        director_client.post('/api/tags/members', json={
            'name': 'John Smith',
            'udisc_name': 'jsmith',
        })
        resp = director_client.post('/api/tags/members/check-duplicate', json={
            'name': 'John Smith',
        })
        assert resp.status_code == 200
        assert resp.json['is_duplicate'] is True
        assert len(resp.json['candidates']) >= 1


class TestEventCreation:
    """Tests for event creation and type handling."""

    def test_create_monthly_event(self, director_client):
        resp = director_client.post('/api/tags/events', json={
            'date': '2026-08-20',
            'event_type': 'monthly',
            'course': 'Iron Hill',
        })
        assert resp.status_code == 201
        assert resp.json['event_type'] == 'monthly'
        assert resp.json['status'] == 'pending'

    def test_create_annual_event(self, director_client):
        resp = director_client.post('/api/tags/events', json={
            'date': '2026-01-15',
            'event_type': 'annual',
            'course': 'Championship Park',
        })
        assert resp.status_code == 201
        assert resp.json['event_type'] == 'annual'

    def test_event_requires_type(self, director_client):
        resp = director_client.post('/api/tags/events', json={
            'date': '2026-08-20',
        })
        assert resp.status_code == 400

    def test_event_requires_date(self, director_client):
        resp = director_client.post('/api/tags/events', json={
            'event_type': 'monthly',
        })
        assert resp.status_code == 400

    def test_event_rejects_invalid_type(self, director_client):
        resp = director_client.post('/api/tags/events', json={
            'date': '2026-08-20',
            'event_type': 'biweekly',
        })
        assert resp.status_code == 400

    def test_pending_events_hidden_from_viewers(self, director_client, client):
        """Pending events are not visible to unauthenticated users."""
        director_client.post('/api/tags/events', json={
            'date': '2026-08-20',
            'event_type': 'monthly',
            'course': 'Hidden Course',
        })
        resp = client.get('/api/tags/events')
        assert resp.status_code == 200
        assert not any(e['course'] == 'Hidden Course' for e in resp.json)

    def test_pending_events_visible_to_directors(self, director_client):
        director_client.post('/api/tags/events', json={
            'date': '2026-08-20',
            'event_type': 'monthly',
            'course': 'Director Course',
        })
        resp = director_client.get('/api/tags/events')
        assert resp.status_code == 200
        assert any(e['course'] == 'Director Course' for e in resp.json)


class TestMonthlyEventLifecycle:
    """Full lifecycle test for a Monthly bag tag event."""

    @pytest.fixture
    def setup_monthly(self, director_client, admin_client):
        """Set up inventory and members for a monthly event."""
        # Set up inventory
        admin_client.post('/api/tags/inventory', json={
            'season_year': 2026,
            'total_tags': 50,
        })

        # Create members with current tags
        members = []
        for i, name in enumerate(['Alice', 'Bob', 'Charlie', 'Diana', 'Eve'], start=1):
            resp = director_client.post('/api/tags/members', json={
                'name': name,
                'udisc_name': name.lower(),
                'current_tag': i,
            })
            members.append(resp.json)

        # Create monthly event
        resp = director_client.post('/api/tags/events', json={
            'date': '2026-08-20',
            'event_type': 'monthly',
            'course': 'Iron Hill',
        })
        event_id = resp.json['event_id']

        return {'members': members, 'event_id': event_id}

    def test_full_monthly_lifecycle(self, director_client, setup_monthly):
        """Test complete Monthly event: register → schedule → in_progress → scores → complete."""
        event_id = setup_monthly['event_id']
        members = setup_monthly['members']

        # Register all players (same-day for monthly)
        for m in members:
            resp = director_client.post(f'/api/tags/events/{event_id}/register', json={
                'member_id': m['member_id'],
                'is_player': True,
                'is_same_day': True,
                'old_tag': m['current_tag'],
            })
            assert resp.status_code == 201
            assert resp.json['is_checked_in'] is True

        # Transition: Pending → Scheduled
        resp = director_client.post(f'/api/tags/events/{event_id}/transition', json={
            'target_status': 'scheduled',
        })
        assert resp.status_code == 200
        assert resp.json['status'] == 'scheduled'

        # Transition: Scheduled → In Progress
        resp = director_client.post(f'/api/tags/events/{event_id}/transition', json={
            'target_status': 'in_progress',
            'season_year': 2026,
        })
        assert resp.status_code == 200
        assert resp.json['status'] == 'in_progress'

        # Submit scores (lower is better)
        scores = [
            {'member_id': members[0]['member_id'], 'round_score': 55},  # Alice - best
            {'member_id': members[1]['member_id'], 'round_score': 58},  # Bob
            {'member_id': members[2]['member_id'], 'round_score': 60},  # Charlie
            {'member_id': members[3]['member_id'], 'round_score': 58},  # Diana (tied with Bob)
            {'member_id': members[4]['member_id'], 'round_score': 62},  # Eve - worst
        ]
        resp = director_client.post(f'/api/tags/events/{event_id}/scores', json={
            'scores': scores,
        })
        assert resp.status_code == 200

        # Transition: In Progress → Complete (runs distribution)
        resp = director_client.post(f'/api/tags/events/{event_id}/transition', json={
            'target_status': 'complete',
            'season_year': 2026,
        })
        assert resp.status_code == 200
        assert resp.json['status'] == 'complete'
        results = resp.json['results']
        assert len(results) == 5

        # Verify distribution: Monthly pool = {1, 2, 3, 4, 5}
        # Alice (score 55) → tag 1
        alice = next(r for r in results if r['member_id'] == members[0]['member_id'])
        assert alice['new_tag'] == 1

        # Eve (score 62) → tag 5
        eve = next(r for r in results if r['member_id'] == members[4]['member_id'])
        assert eve['new_tag'] == 5

    def test_monthly_tiebreaker(self, director_client, setup_monthly):
        """Tied scores broken by old_tag (lower old_tag wins)."""
        event_id = setup_monthly['event_id']
        members = setup_monthly['members']

        # Register Bob (tag 2) and Diana (tag 4)
        for m in [members[1], members[3]]:
            director_client.post(f'/api/tags/events/{event_id}/register', json={
                'member_id': m['member_id'],
                'is_player': True,
                'is_same_day': True,
                'old_tag': m['current_tag'],
            })

        # Advance to in_progress
        director_client.post(f'/api/tags/events/{event_id}/transition', json={
            'target_status': 'scheduled',
        })
        director_client.post(f'/api/tags/events/{event_id}/transition', json={
            'target_status': 'in_progress',
            'season_year': 2026,
        })

        # Both score 58
        scores = [
            {'member_id': members[1]['member_id'], 'round_score': 58},  # Bob, old_tag=2
            {'member_id': members[3]['member_id'], 'round_score': 58},  # Diana, old_tag=4
        ]
        director_client.post(f'/api/tags/events/{event_id}/scores', json={'scores': scores})

        # Complete
        resp = director_client.post(f'/api/tags/events/{event_id}/transition', json={
            'target_status': 'complete',
            'season_year': 2026,
        })
        results = resp.json['results']

        bob = next(r for r in results if r['member_id'] == members[1]['member_id'])
        diana = next(r for r in results if r['member_id'] == members[3]['member_id'])

        # Bob (old_tag=2) should beat Diana (old_tag=4) on tiebreaker
        assert bob['position'] < diana['position']
        assert bob['new_tag'] < diana['new_tag']

    def test_monthly_dnf(self, director_client, setup_monthly):
        """DNF players get highest tags from pool, ordered by prev tag desc."""
        event_id = setup_monthly['event_id']
        members = setup_monthly['members']

        # Register all 5 players
        for m in members:
            director_client.post(f'/api/tags/events/{event_id}/register', json={
                'member_id': m['member_id'],
                'is_player': True,
                'is_same_day': True,
                'old_tag': m['current_tag'],
            })

        # Advance to in_progress
        director_client.post(f'/api/tags/events/{event_id}/transition', json={
            'target_status': 'scheduled',
        })
        director_client.post(f'/api/tags/events/{event_id}/transition', json={
            'target_status': 'in_progress',
            'season_year': 2026,
        })

        # Mark Eve (tag 5) and Diana (tag 4) as DNF
        event_resp = director_client.get(f'/api/tags/events/{event_id}')
        regs = event_resp.json['registrations']
        eve_reg = next(r for r in regs if r['member_id'] == members[4]['member_id'])
        diana_reg = next(r for r in regs if r['member_id'] == members[3]['member_id'])

        director_client.put(
            f'/api/tags/events/{event_id}/registrations/{eve_reg["reg_id"]}',
            json={'is_dnf': True}
        )
        director_client.put(
            f'/api/tags/events/{event_id}/registrations/{diana_reg["reg_id"]}',
            json={'is_dnf': True}
        )

        # Submit scores for the 3 non-DNF players
        scores = [
            {'member_id': members[0]['member_id'], 'round_score': 55},  # Alice, tag 1
            {'member_id': members[1]['member_id'], 'round_score': 58},  # Bob, tag 2
            {'member_id': members[2]['member_id'], 'round_score': 60},  # Charlie, tag 3
        ]
        director_client.post(f'/api/tags/events/{event_id}/scores', json={'scores': scores})

        # Complete
        resp = director_client.post(f'/api/tags/events/{event_id}/transition', json={
            'target_status': 'complete',
            'season_year': 2026,
        })
        results = resp.json['results']

        # Pool is {1, 2, 3, 4, 5}
        # DNF players: Eve (old_tag=5) and Diana (old_tag=4)
        # Eve gets tag 5 (highest), Diana gets tag 4
        eve = next(r for r in results if r['member_id'] == members[4]['member_id'])
        diana = next(r for r in results if r['member_id'] == members[3]['member_id'])
        assert eve['new_tag'] == 5  # highest DNF old_tag → highest pool tag
        assert diana['new_tag'] == 4
        assert eve['is_dnf'] is True
        assert diana['is_dnf'] is True

        # Remaining players get tags 1, 2, 3
        alice = next(r for r in results if r['member_id'] == members[0]['member_id'])
        assert alice['new_tag'] == 1

    def test_monthly_same_day_new_member(self, director_client, admin_client, setup_monthly):
        """Same-day registration for a new member assigns lowest available tag."""
        event_id = setup_monthly['event_id']
        members = setup_monthly['members']

        # Create a new member without a tag
        resp = director_client.post('/api/tags/members', json={
            'name': 'Newbie Nick',
            'udisc_name': 'newbie_nick',
        })
        new_member_id = resp.json['member_id']

        # Register existing members first
        for m in members[:3]:
            director_client.post(f'/api/tags/events/{event_id}/register', json={
                'member_id': m['member_id'],
                'is_player': True,
                'is_same_day': True,
                'old_tag': m['current_tag'],
            })

        # Same-day register new member — should get lowest available from inventory
        # Members 1-5 have tags 1-5, so lowest available is 6
        resp = director_client.post(f'/api/tags/events/{event_id}/register', json={
            'member_id': new_member_id,
            'is_player': True,
            'is_same_day': True,
        })
        assert resp.status_code == 201
        assert resp.json['old_tag'] == 6  # lowest available from inventory
        assert resp.json['is_checked_in'] is True


class TestAnnualEventLifecycle:
    """Tests specific to Annual bag tag events."""

    @pytest.fixture
    def setup_annual(self, director_client, admin_client):
        """Set up inventory and members for an annual event."""
        # Set up inventory
        admin_client.post('/api/tags/inventory', json={
            'season_year': 2026,
            'total_tags': 100,
        })

        # Create event
        resp = director_client.post('/api/tags/events', json={
            'date': '2026-01-15',
            'event_type': 'annual',
            'course': 'Championship Park',
        })
        event_id = resp.json['event_id']

        return {'event_id': event_id}

    def test_annual_pool_is_1_to_n(self, director_client, admin_client, setup_annual):
        """Annual event pool is 1..n where n = checked-in players."""
        event_id = setup_annual['event_id']

        # Create and register 5 players
        member_ids = []
        for i, name in enumerate(['P1', 'P2', 'P3', 'P4', 'P5'], start=1):
            resp = director_client.post('/api/tags/members', json={
                'name': name,
                'udisc_name': name.lower(),
            })
            mid = resp.json['member_id']
            member_ids.append(mid)

            # Register with previous year's tag as old_tag
            director_client.post(f'/api/tags/events/{event_id}/register', json={
                'member_id': mid,
                'is_player': True,
                'old_tag': i * 10,  # previous year's tags: 10, 20, 30, 40, 50
            })

        # Advance to scheduled
        director_client.post(f'/api/tags/events/{event_id}/transition', json={
            'target_status': 'scheduled',
        })

        # Check in all players
        for mid in member_ids:
            director_client.post(f'/api/tags/events/{event_id}/checkin', json={
                'member_id': mid,
            })

        # Advance to in_progress
        director_client.post(f'/api/tags/events/{event_id}/transition', json={
            'target_status': 'in_progress',
            'season_year': 2026,
        })

        # Submit scores
        scores = [
            {'member_id': member_ids[0], 'round_score': 55},
            {'member_id': member_ids[1], 'round_score': 58},
            {'member_id': member_ids[2], 'round_score': 60},
            {'member_id': member_ids[3], 'round_score': 58},
            {'member_id': member_ids[4], 'round_score': 62},
        ]
        director_client.post(f'/api/tags/events/{event_id}/scores', json={'scores': scores})

        # Complete
        resp = director_client.post(f'/api/tags/events/{event_id}/transition', json={
            'target_status': 'complete',
            'season_year': 2026,
        })
        results = resp.json['results']

        # Pool should be 1-5 (not the old_tag values)
        new_tags = sorted([r['new_tag'] for r in results])
        assert new_tags == [1, 2, 3, 4, 5]

    def test_annual_non_player_assignment(self, director_client, admin_client, setup_annual):
        """Non-players get highest available tags from inventory."""
        event_id = setup_annual['event_id']

        # Create 3 players and 2 non-players
        players = []
        for i in range(3):
            resp = director_client.post('/api/tags/members', json={
                'name': f'Player {i}', 'udisc_name': f'player{i}',
            })
            mid = resp.json['member_id']
            players.append(mid)
            director_client.post(f'/api/tags/events/{event_id}/register', json={
                'member_id': mid,
                'is_player': True,
                'old_tag': (i + 1) * 10,
            })

        # Non-player with previous tag
        resp = director_client.post('/api/tags/members', json={
            'name': 'NonPlayer WithTag', 'udisc_name': 'np_with',
        })
        np_with_tag = resp.json['member_id']
        director_client.post(f'/api/tags/events/{event_id}/register', json={
            'member_id': np_with_tag,
            'is_player': False,
            'old_tag': 50,  # had tag 50 last year
        })

        # Non-player without previous tag
        resp = director_client.post('/api/tags/members', json={
            'name': 'NonPlayer NoTag', 'udisc_name': 'np_no',
        })
        np_no_tag = resp.json['member_id']
        director_client.post(f'/api/tags/events/{event_id}/register', json={
            'member_id': np_no_tag,
            'is_player': False,
        })

        # Schedule
        director_client.post(f'/api/tags/events/{event_id}/transition', json={
            'target_status': 'scheduled',
        })

        # Check in players only
        for mid in players:
            director_client.post(f'/api/tags/events/{event_id}/checkin', json={
                'member_id': mid,
            })

        # Advance to in_progress — should assign non-player tags
        resp = director_client.post(f'/api/tags/events/{event_id}/transition', json={
            'target_status': 'in_progress',
            'season_year': 2026,
        })
        assert resp.status_code == 200
        details = resp.json['details']

        # Non-player assignments should use highest available from inventory (100 total)
        # Players+non-players have tags assigned via current_tag, but since these are new members
        # with no current_tag, the highest available should be 99, 100
        np_assignments = details['non_player_assignments']
        assert len(np_assignments) == 2

        # Non-player without previous tag should be assigned first (highest available)
        assigned_tags = sorted([a['new_tag'] for a in np_assignments], reverse=True)
        assert assigned_tags[0] == 100
        assert assigned_tags[1] == 99

    def test_annual_dnf_for_unchecked_players(self, director_client, admin_client, setup_annual):
        """Players who don't check in are auto-DNF'd at Scheduled → In Progress."""
        event_id = setup_annual['event_id']

        # Register 3 players
        member_ids = []
        for i, name in enumerate(['Checked', 'AlsoChecked', 'NoShow']):
            resp = director_client.post('/api/tags/members', json={
                'name': name, 'udisc_name': name.lower(),
            })
            mid = resp.json['member_id']
            member_ids.append(mid)
            director_client.post(f'/api/tags/events/{event_id}/register', json={
                'member_id': mid,
                'is_player': True,
                'old_tag': (i + 1) * 5,
            })

        # Schedule
        director_client.post(f'/api/tags/events/{event_id}/transition', json={
            'target_status': 'scheduled',
        })

        # Only check in first 2
        for mid in member_ids[:2]:
            director_client.post(f'/api/tags/events/{event_id}/checkin', json={
                'member_id': mid,
            })

        # Advance to in_progress — NoShow should be DNF'd
        resp = director_client.post(f'/api/tags/events/{event_id}/transition', json={
            'target_status': 'in_progress',
            'season_year': 2026,
        })
        details = resp.json['details']
        assert len(details['dnf_players']) == 1
        assert details['dnf_players'][0]['name'] == 'NoShow'


class TestStateTransitions:
    """Tests for invalid state transitions and error handling."""

    def test_cannot_skip_states(self, director_client):
        """Cannot jump from pending directly to in_progress."""
        resp = director_client.post('/api/tags/events', json={
            'date': '2026-08-20',
            'event_type': 'monthly',
        })
        event_id = resp.json['event_id']

        resp = director_client.post(f'/api/tags/events/{event_id}/transition', json={
            'target_status': 'in_progress',
            'season_year': 2026,
        })
        assert resp.status_code == 400

    def test_cannot_go_backwards(self, director_client):
        """Cannot transition from scheduled back to pending."""
        resp = director_client.post('/api/tags/events', json={
            'date': '2026-08-20',
            'event_type': 'monthly',
        })
        event_id = resp.json['event_id']

        # Advance to scheduled
        director_client.post(f'/api/tags/events/{event_id}/transition', json={
            'target_status': 'scheduled',
        })

        # Try going back to pending
        resp = director_client.post(f'/api/tags/events/{event_id}/transition', json={
            'target_status': 'pending',
        })
        assert resp.status_code == 400

    def test_cannot_complete_without_scores(self, director_client, admin_client):
        """Cannot complete an event without any scores submitted."""
        admin_client.post('/api/tags/inventory', json={
            'season_year': 2026, 'total_tags': 50,
        })

        resp = director_client.post('/api/tags/events', json={
            'date': '2026-08-20',
            'event_type': 'monthly',
        })
        event_id = resp.json['event_id']

        # Register a player
        resp = director_client.post('/api/tags/members', json={
            'name': 'Solo Player', 'current_tag': 1,
        })
        mid = resp.json['member_id']
        director_client.post(f'/api/tags/events/{event_id}/register', json={
            'member_id': mid,
            'is_player': True,
            'is_same_day': True,
            'old_tag': 1,
        })

        # Advance through states without submitting scores
        director_client.post(f'/api/tags/events/{event_id}/transition', json={
            'target_status': 'scheduled',
        })
        director_client.post(f'/api/tags/events/{event_id}/transition', json={
            'target_status': 'in_progress',
            'season_year': 2026,
        })

        # Try to complete
        resp = director_client.post(f'/api/tags/events/{event_id}/transition', json={
            'target_status': 'complete',
            'season_year': 2026,
        })
        assert resp.status_code == 400

    def test_registration_blocked_after_scheduled(self, director_client, admin_client):
        """Cannot register new players after event is in_progress."""
        admin_client.post('/api/tags/inventory', json={
            'season_year': 2026, 'total_tags': 50,
        })

        resp = director_client.post('/api/tags/events', json={
            'date': '2026-08-20',
            'event_type': 'monthly',
        })
        event_id = resp.json['event_id']

        # Register and advance
        resp = director_client.post('/api/tags/members', json={
            'name': 'First', 'current_tag': 1,
        })
        mid = resp.json['member_id']
        director_client.post(f'/api/tags/events/{event_id}/register', json={
            'member_id': mid, 'is_player': True, 'is_same_day': True, 'old_tag': 1,
        })
        director_client.post(f'/api/tags/events/{event_id}/transition', json={
            'target_status': 'scheduled',
        })
        director_client.post(f'/api/tags/events/{event_id}/transition', json={
            'target_status': 'in_progress', 'season_year': 2026,
        })

        # Try to register another player
        resp = director_client.post('/api/tags/members', json={
            'name': 'Late', 'current_tag': 2,
        })
        mid2 = resp.json['member_id']
        resp = director_client.post(f'/api/tags/events/{event_id}/register', json={
            'member_id': mid2, 'is_player': True, 'is_same_day': True, 'old_tag': 2,
        })
        assert resp.status_code == 400

    def test_scores_blocked_before_in_progress(self, director_client):
        """Cannot submit scores for a pending or scheduled event."""
        resp = director_client.post('/api/tags/events', json={
            'date': '2026-08-20',
            'event_type': 'monthly',
        })
        event_id = resp.json['event_id']

        resp = director_client.post(f'/api/tags/events/{event_id}/scores', json={
            'scores': [{'member_id': 1, 'round_score': 55}],
        })
        assert resp.status_code == 400


class TestInventoryManagement:
    """Tests for tag inventory endpoints."""

    def test_set_and_get_inventory(self, admin_client):
        resp = admin_client.post('/api/tags/inventory', json={
            'season_year': 2026,
            'total_tags': 100,
        })
        assert resp.status_code == 200

        resp = admin_client.get('/api/tags/inventory?year=2026')
        assert resp.status_code == 200
        data = resp.json
        assert data['total_tags'] == 100
        assert data['available_count'] == 100

    def test_available_tags_excludes_assigned(self, admin_client, director_client):
        """Available tags should not include tags assigned to members."""
        admin_client.post('/api/tags/inventory', json={
            'season_year': 2026, 'total_tags': 10,
        })

        # Create member with tag 3
        director_client.post('/api/tags/members', json={
            'name': 'Tag Holder',
            'current_tag': 3,
        })

        resp = admin_client.get('/api/tags/inventory?year=2026')
        assert 3 not in resp.json['available_tags']
        assert resp.json['available_count'] == 9

    def test_mark_tag_unavailable(self, admin_client):
        admin_client.post('/api/tags/inventory', json={
            'season_year': 2026, 'total_tags': 10,
        })

        resp = admin_client.post('/api/tags/inventory/unavailable', json={
            'season_year': 2026,
            'tag_number': 5,
            'reason': 'lost',
        })
        assert resp.status_code == 200

        resp = admin_client.get('/api/tags/inventory?year=2026')
        assert 5 not in resp.json['available_tags']
        assert resp.json['available_count'] == 9
        assert any(u['tag_number'] == 5 for u in resp.json['unavailable_tags'])

    def test_restore_unavailable_tag(self, admin_client):
        admin_client.post('/api/tags/inventory', json={
            'season_year': 2026, 'total_tags': 10,
        })
        admin_client.post('/api/tags/inventory/unavailable', json={
            'season_year': 2026, 'tag_number': 5,
        })

        resp = admin_client.delete('/api/tags/inventory/unavailable', json={
            'season_year': 2026, 'tag_number': 5,
        })
        assert resp.status_code == 200

        resp = admin_client.get('/api/tags/inventory?year=2026')
        assert 5 in resp.json['available_tags']

    def test_cannot_set_total_below_highest_assigned(self, admin_client, director_client):
        """Cannot set total_tags below the highest currently assigned tag."""
        admin_client.post('/api/tags/inventory', json={
            'season_year': 2026, 'total_tags': 100,
        })
        director_client.post('/api/tags/members', json={
            'name': 'High Tag', 'current_tag': 50,
        })

        resp = admin_client.post('/api/tags/inventory', json={
            'season_year': 2026, 'total_tags': 40,
        })
        assert resp.status_code == 400

    def test_inventory_requires_admin(self, director_client):
        """Directors cannot manage inventory."""
        resp = director_client.post('/api/tags/inventory', json={
            'season_year': 2026, 'total_tags': 100,
        })
        assert resp.status_code == 403

    def test_assign_tag_to_member(self, admin_client, director_client):
        """Assign a tag to a member outside of an event."""
        admin_client.post('/api/tags/inventory', json={
            'season_year': 2026, 'total_tags': 50,
        })
        resp = director_client.post('/api/tags/members', json={
            'name': 'New Member',
        })
        mid = resp.json['member_id']

        # Assign lowest available
        resp = director_client.post(f'/api/tags/members/{mid}/assign-tag', json={
            'season_year': 2026,
        })
        assert resp.status_code == 200
        assert resp.json['current_tag'] == 1  # lowest available

    def test_assign_specific_tag(self, admin_client, director_client):
        """Assign a specific tag number to a member."""
        admin_client.post('/api/tags/inventory', json={
            'season_year': 2026, 'total_tags': 50,
        })
        resp = director_client.post('/api/tags/members', json={
            'name': 'Specific Tag Member',
        })
        mid = resp.json['member_id']

        resp = director_client.post(f'/api/tags/members/{mid}/assign-tag', json={
            'season_year': 2026,
            'tag_number': 25,
        })
        assert resp.status_code == 200
        assert resp.json['current_tag'] == 25

    def test_cannot_assign_unavailable_tag(self, admin_client, director_client):
        """Cannot assign a tag that is marked unavailable."""
        admin_client.post('/api/tags/inventory', json={
            'season_year': 2026, 'total_tags': 50,
        })
        admin_client.post('/api/tags/inventory/unavailable', json={
            'season_year': 2026, 'tag_number': 10, 'reason': 'lost',
        })
        resp = director_client.post('/api/tags/members', json={
            'name': 'Wants Lost Tag',
        })
        mid = resp.json['member_id']

        resp = director_client.post(f'/api/tags/members/{mid}/assign-tag', json={
            'season_year': 2026,
            'tag_number': 10,
        })
        assert resp.status_code == 400


class TestScoreImport:
    """Tests for CSV/XLSX score import with matching."""

    def test_import_csv_scores(self, director_client, admin_client):
        """Import scores from a CSV file with UDisc name matching."""
        admin_client.post('/api/tags/inventory', json={
            'season_year': 2026, 'total_tags': 50,
        })

        # Create members with UDisc names
        members = []
        for name, udisc in [('Alice A', 'alice_a'), ('Bob B', 'bob_b'), ('Charlie C', 'charlie_c')]:
            resp = director_client.post('/api/tags/members', json={
                'name': name,
                'udisc_name': udisc,
                'current_tag': len(members) + 1,
            })
            members.append(resp.json)

        # Create event and register
        resp = director_client.post('/api/tags/events', json={
            'date': '2026-08-20',
            'event_type': 'monthly',
        })
        event_id = resp.json['event_id']

        for m in members:
            director_client.post(f'/api/tags/events/{event_id}/register', json={
                'member_id': m['member_id'],
                'is_player': True,
                'is_same_day': True,
                'old_tag': m['current_tag'],
            })

        # Advance to in_progress
        director_client.post(f'/api/tags/events/{event_id}/transition', json={
            'target_status': 'scheduled',
        })
        director_client.post(f'/api/tags/events/{event_id}/transition', json={
            'target_status': 'in_progress',
            'season_year': 2026,
        })

        # Import CSV scores
        csv_content = "Name,Total\nalice_a,55\nbob_b,60\ncharlie_c,58\n"
        data = {
            'file': (io.BytesIO(csv_content.encode()), 'results.csv'),
        }
        resp = director_client.post(
            f'/api/tags/events/{event_id}/scores/import',
            content_type='multipart/form-data',
            data=data,
        )
        assert resp.status_code == 200
        assert resp.json['applied'] == 3
        assert resp.json['needs_resolution'] is False

    def test_import_unmatched_scores(self, director_client, admin_client):
        """Unmatched scores return candidates for manual resolution."""
        admin_client.post('/api/tags/inventory', json={
            'season_year': 2026, 'total_tags': 50,
        })

        resp = director_client.post('/api/tags/members', json={
            'name': 'Alice Adams',
            'udisc_name': 'alice_a',
            'current_tag': 1,
        })
        mid = resp.json['member_id']

        resp = director_client.post('/api/tags/events', json={
            'date': '2026-08-20',
            'event_type': 'monthly',
        })
        event_id = resp.json['event_id']

        director_client.post(f'/api/tags/events/{event_id}/register', json={
            'member_id': mid,
            'is_player': True,
            'is_same_day': True,
            'old_tag': 1,
        })

        director_client.post(f'/api/tags/events/{event_id}/transition', json={
            'target_status': 'scheduled',
        })
        director_client.post(f'/api/tags/events/{event_id}/transition', json={
            'target_status': 'in_progress', 'season_year': 2026,
        })

        # CSV with a name that doesn't match
        csv_content = "Name,Total\nalice_a,55\nunknown_player,60\n"
        data = {
            'file': (io.BytesIO(csv_content.encode()), 'results.csv'),
        }
        resp = director_client.post(
            f'/api/tags/events/{event_id}/scores/import',
            content_type='multipart/form-data',
            data=data,
        )
        assert resp.status_code == 200
        assert resp.json['applied'] == 1
        assert resp.json['needs_resolution'] is True
        assert len(resp.json['unmatched']) == 1
        assert resp.json['unmatched'][0]['import_name'] == 'unknown_player'


class TestRegistrationImport:
    """Tests for bulk CSV registration import."""

    def test_import_dgscene_csv(self, director_client):
        """Import members from a DGScene CSV file."""
        resp = director_client.post('/api/tags/events', json={
            'date': '2026-01-15',
            'event_type': 'annual',
            'course': 'Annual Park',
        })
        event_id = resp.json['event_id']

        csv_content = (
            'Division,Name,"First name","Last name",PDGA#,Email,Phone,'
            '"Entry fee $","Last Year\'s Tag","Last Year\'s Tag $",'
            '"2023 Tag Number",Address,City,State,ZIP,Country,'
            '"Registration date PST",Notes\n'
            'AFTN,"John Smith",John,Smith,12345,john@example.com,555-1234,'
            '35,,,25,"123 Main St","San Jose",CA,95112,US,'
            '"2026-01-01 10:00:00",\n'
            'AFTN,"Jane Doe",Jane,Doe,67890,jane@example.com,555-5678,'
            '35,,,30,"456 Oak Ave","Sunnyvale",CA,94087,US,'
            '"2026-01-02 11:00:00",\n'
        )

        data = {
            'file': (io.BytesIO(csv_content.encode()), 'registrations.csv'),
        }
        resp = director_client.post(
            f'/api/tags/events/{event_id}/register/import',
            content_type='multipart/form-data',
            data=data,
        )
        assert resp.status_code == 200
        assert resp.json['registered'] == 2
        assert resp.json['created_members'] == 2

    def test_import_blocked_after_pending(self, director_client):
        """Cannot import registrations once event leaves pending."""
        resp = director_client.post('/api/tags/events', json={
            'date': '2026-01-15',
            'event_type': 'annual',
        })
        event_id = resp.json['event_id']

        # Advance to scheduled
        director_client.post(f'/api/tags/events/{event_id}/transition', json={
            'target_status': 'scheduled',
        })

        csv_content = 'Division,Name\nAFTN,"Late Import"\n'
        data = {
            'file': (io.BytesIO(csv_content.encode()), 'registrations.csv'),
        }
        resp = director_client.post(
            f'/api/tags/events/{event_id}/register/import',
            content_type='multipart/form-data',
            data=data,
        )
        assert resp.status_code == 400


class TestStandingsAndHistory:
    """Tests for standings and history endpoints."""

    def test_standings_public(self, client, director_client):
        """Standings are publicly accessible."""
        director_client.post('/api/tags/members', json={
            'name': 'Public Player', 'current_tag': 1,
        })
        resp = client.get('/api/tags/standings')
        assert resp.status_code == 200
        assert len(resp.json) >= 1

    def test_standings_sorted_by_tag(self, director_client):
        """Standings are sorted by tag number ascending."""
        for tag in [5, 1, 3]:
            director_client.post('/api/tags/members', json={
                'name': f'Player {tag}', 'current_tag': tag,
            })

        resp = director_client.get('/api/tags/standings')
        tags = [s['current_tag'] for s in resp.json]
        assert tags == sorted(tags)

    def test_member_history(self, director_client, admin_client):
        """Member history shows event participation."""
        admin_client.post('/api/tags/inventory', json={
            'season_year': 2026, 'total_tags': 50,
        })

        # Create 2 members
        resp = director_client.post('/api/tags/members', json={
            'name': 'Historian', 'udisc_name': 'historian', 'current_tag': 5,
        })
        mid1 = resp.json['member_id']
        resp = director_client.post('/api/tags/members', json={
            'name': 'Other', 'udisc_name': 'other', 'current_tag': 3,
        })
        mid2 = resp.json['member_id']

        # Run a monthly event
        resp = director_client.post('/api/tags/events', json={
            'date': '2026-08-15',
            'event_type': 'monthly',
            'course': 'History Course',
        })
        eid = resp.json['event_id']

        for mid, tag in [(mid1, 5), (mid2, 3)]:
            director_client.post(f'/api/tags/events/{eid}/register', json={
                'member_id': mid, 'is_player': True, 'is_same_day': True, 'old_tag': tag,
            })

        director_client.post(f'/api/tags/events/{eid}/transition', json={
            'target_status': 'scheduled',
        })
        director_client.post(f'/api/tags/events/{eid}/transition', json={
            'target_status': 'in_progress', 'season_year': 2026,
        })

        director_client.post(f'/api/tags/events/{eid}/scores', json={
            'scores': [
                {'member_id': mid1, 'round_score': 50},  # Historian wins
                {'member_id': mid2, 'round_score': 60},
            ],
        })

        director_client.post(f'/api/tags/events/{eid}/transition', json={
            'target_status': 'complete', 'season_year': 2026,
        })

        # Check history
        resp = director_client.get(f'/api/tags/members/{mid1}/history')
        assert resp.status_code == 200
        history = resp.json
        assert len(history) == 1
        assert history[0]['old_tag'] == 5
        assert history[0]['new_tag'] == 3  # Won the lower tag
        assert history[0]['is_dnf'] is False

    def test_history_nonexistent_member(self, client):
        resp = client.get('/api/tags/members/9999/history')
        assert resp.status_code == 404
