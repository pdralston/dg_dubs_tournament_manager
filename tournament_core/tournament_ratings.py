#!/usr/bin/env python3
"""
Tournament-Style Disc Golf League Rating System

This module implements a rating system for a doubles disc golf league
backed by MySQL via Flask-SQLAlchemy.
"""

import datetime
import math
from typing import Dict, List, Tuple, Optional, Any

from .tournament_db_manager import TournamentDBManager


class TournamentRatingSystem:
    def __init__(self):
        """Initialize the rating system. Requires Flask app context."""
        self.db_manager = TournamentDBManager()
        self.players = {}
        self.tournaments = []

        # Import ace pot manager
        from .ace_pot_manager import AcePotManager
        self.ace_pot_manager = AcePotManager(self.db_manager)

    def load_data(self):
        """Load player and tournament data from the database."""
        self._load_from_db()

    def _load_from_db(self):
        """Load player and tournament data from database."""
        players_data = self.db_manager.get_all_players()
        self.players = {}

        for player in players_data:
            name = player['name']
            self.players[name] = {
                'rating': player['rating'],
                'tournaments_played': player['tournaments_played'],
                'is_club_member': player.get('is_club_member', False),
                'history': [],
            }
            history_entries = self.db_manager.get_player_history(name)
            for entry in history_entries:
                self.players[name]['history'].append({
                    'tournament_date': entry['tournament_date'],
                    'old_rating': entry['old_rating'],
                    'new_rating': entry['new_rating'],
                    'position': entry['position'],
                    'expected_position': entry['expected_position'],
                    'score': entry['score'],
                    'with_ghost': bool(entry['with_ghost']),
                    'change': entry['new_rating'] - entry['old_rating'],
                })

        tournaments_data = self.db_manager.get_tournaments()
        self.tournaments = []
        for tournament in tournaments_data:
            td = {
                'id': tournament['id'],
                'date': tournament['date'],
                'course': tournament['course'],
                'teams': tournament['team_count'],
                'results': [],
            }
            for result in tournament['results']:
                td['results'].append({
                    'team': [result['player1_name'], result['player2_name']],
                    'position': result['position'],
                    'expected_position': result['expected_position'],
                    'score': result['score'],
                    'team_rating': result['team_rating'],
                    'payout': result.get('payout', 0),
                })
            self.tournaments.append(td)

    # ── Lookup helpers ───────────────────────────────────────────────

    def _create_case_insensitive_lookup(self) -> Dict[str, str]:
        return {name.lower(): name for name in self.players.keys()}

    def player_exists(self, name: str) -> bool:
        if name == "Ghost Player":
            return True
        return name.lower() in self._create_case_insensitive_lookup()

    def get_player(self, name: str) -> Dict[str, Any]:
        if name == "Ghost Player":
            return {'rating': self.get_ghost_player_rating(), 'tournaments_played': 0, 'history': []}
        lookup = self._create_case_insensitive_lookup()
        if name.lower() in lookup:
            return self.players[lookup[name.lower()]]
        raise ValueError(f"Player {name} not found")

    def get_player_name(self, name: str) -> str:
        if name == "Ghost Player":
            return "Ghost Player"
        lookup = self._create_case_insensitive_lookup()
        if name.lower() in lookup:
            return lookup[name.lower()]
        raise ValueError(f"Player {name} not found")

    # ── Player management ────────────────────────────────────────────

    def add_player(self, name: str, initial_rating: int = 1000, is_club_member: bool = False):
        if self.player_exists(name):
            raise ValueError(f"Player {name} already exists")

        self.db_manager.add_player(name, initial_rating, is_club_member)
        self.players[name] = {
            'rating': initial_rating,
            'tournaments_played': 0,
            'history': [],
            'is_club_member': is_club_member,
        }
        print(f"Added player {name} with initial rating {initial_rating}")

    def update_player_club_membership(self, name: str, is_club_member: bool):
        if not self.player_exists(name):
            raise ValueError(f"Player {name} not found")
        player_name = self.get_player_name(name)
        self.players[player_name]['is_club_member'] = is_club_member
        self.db_manager.update_player_club_membership(player_name, is_club_member)

    # ── Rating helpers ───────────────────────────────────────────────

    def get_k_factor(self, player: str) -> float:
        tp = self.get_player(player)['tournaments_played']
        if tp < 5:
            return 10
        elif tp < 15:
            return 5
        return 1

    def get_ghost_player_rating(self) -> float:
        if not self.players:
            return 1000
        return sum(p['rating'] for p in self.players.values()) / len(self.players)

    def calculate_team_rating(self, player1: str, player2: str) -> float:
        if player1 == "Ghost Player":
            return self.get_player(player2)['rating']
        if player2 == "Ghost Player":
            return self.get_player(player1)['rating']
        return (self.get_player(player1)['rating'] + self.get_player(player2)['rating']) / 2

    # ── Predictions ──────────────────────────────────────────────────

    def predict_tournament_outcome(self, teams: List[Tuple[str, str]]) -> Dict[Tuple[str, str], Dict[str, Any]]:
        team_ratings = {}
        for team in teams:
            for p in team:
                if p != "Ghost Player" and not self.player_exists(p):
                    raise ValueError(f"Player {p} not found")
            team_ratings[team] = self.calculate_team_rating(team[0], team[1])

        expected_position = 1
        previous_rating = 0
        predictions = {}
        for team, rating in sorted(team_ratings.items(), key=lambda x: x[1], reverse=True):
            if previous_rating > rating:
                expected_position += 1
            previous_rating = rating
            predictions[team] = {'team': team, 'rating': rating, 'expected_position': expected_position}
        return predictions

    def predict_scores(self, teams: List[Tuple[str, str]], par: int = 54) -> Dict[Tuple[str, str], float]:
        team_ratings = {t: self.calculate_team_rating(t[0], t[1]) for t in teams}
        avg_rating = sum(team_ratings.values()) / len(team_ratings)
        return {t: par + (-0.25 * ((r - avg_rating) / 10)) for t, r in team_ratings.items()}

    # ── Tournament recording ─────────────────────────────────────────

    def record_tournament(self, team_results: List[Tuple[Tuple[str, str], int]],
                          course_name: str = None, date: str = None,
                          ace_pot_paid: bool = False) -> Optional[int]:
        if date is None:
            date = datetime.datetime.now().strftime("%Y-%m-%d")

        teams = [team for team, _ in team_results]
        for p1, p2 in teams:
            for p in (p1, p2):
                if p != "Ghost Player" and not self.player_exists(p):
                    raise ValueError(f"Player {p} not found")

        predictions = self.predict_tournament_outcome(teams)

        tournament_id = self.db_manager.add_tournament(date, course_name, len(teams), ace_pot_paid)
        if tournament_id is None:
            print("Error: Failed to add tournament to database")
            return None

        tournament = {
            'id': tournament_id, 'date': date, 'course': course_name,
            'teams': len(teams), 'results': [],
        }

        for position, (team, score) in self.resolve_tournament_positions(team_results):
            player1, player2 = team
            if player1 != "Ghost Player":
                player1 = self.get_player_name(player1)
            if player2 != "Ghost Player":
                player2 = self.get_player_name(player2)

            team_rating = self.calculate_team_rating(player1, player2)
            expected_position = predictions[team]['expected_position']
            position_diff = expected_position - position

            midpoint = len(teams) / 2
            max_diff = len(teams) - midpoint
            mid_diff = midpoint - position
            overall_modifier = mid_diff * abs(mid_diff / max_diff)

            tournament['results'].append({
                'team': [player1, player2], 'score': score, 'position': position,
                'expected_position': expected_position, 'team_rating': team_rating,
            })

            self.db_manager.add_team_result(
                tournament_id, player1, player2, position,
                expected_position, score, team_rating,
            )

            for player in [player1, player2]:
                if player == "Ghost Player":
                    continue
                k_factor = self.get_k_factor(player)
                player_data = self.get_player(player)
                old_rating = player_data['rating']
                tournament_bonus = 1 + (len(teams) - 4) * 0.05
                adjustment = k_factor * (position_diff + overall_modifier) * tournament_bonus
                new_rating = old_rating + adjustment

                player_data['rating'] = new_rating
                player_data['tournaments_played'] += 1
                player_data['history'].append({
                    'tournament_date': date, 'old_rating': old_rating,
                    'new_rating': new_rating, 'change': new_rating - old_rating,
                    'position': position, 'expected_position': expected_position,
                    'score': score, 'with_ghost': "Ghost Player" in [player1, player2],
                })

                self.db_manager.update_player_rating(player, new_rating)
                self.db_manager.increment_player_tournaments(player)
                self.db_manager.add_player_history(
                    player, tournament_id, old_rating, new_rating,
                    position, expected_position, score,
                    "Ghost Player" in [player1, player2],
                )

        self.tournaments.append(tournament)
        self.db_manager.commit_transaction()
        print(f"Tournament recorded with {len(teams)} teams (ID: {tournament_id})")
        return tournament_id

    def resolve_tournament_positions(self, team_results):
        sorted_results = sorted(team_results, key=lambda x: x[1])
        positions = []
        current_position = 1
        current_score = None
        for i, (team, score) in enumerate(sorted_results):
            if i == 0 or score != current_score:
                current_position = i + 1
                current_score = score
            positions.append((current_position, (team, score)))
        return positions

    # ── Team generation ──────────────────────────────────────────────

    def generate_balanced_teams(self, players: List[str]) -> List[Tuple[str, str]]:
        for p in players:
            if not self.player_exists(p):
                raise ValueError(f"Player {p} not found")
        players = [self.get_player_name(p) for p in players]

        if len(players) % 2 == 1:
            players.append("Ghost Player")

        sorted_players = sorted(
            players,
            key=lambda p: self.get_player(p)['rating'] if p != "Ghost Player" else 0,
            reverse=True,
        )
        teams = []
        while sorted_players:
            p1 = sorted_players.pop(0)
            p2 = sorted_players.pop(-1) if sorted_players else "Ghost Player"
            teams.append((p1, p2))
        return teams

    # ── Details ──────────────────────────────────────────────────────

    def get_player_details(self, name: str) -> Dict[str, Any]:
        player_data = self.get_player(name)
        return {
            'name': self.get_player_name(name),
            'rating': player_data['rating'],
            'tournaments_played': player_data['tournaments_played'],
            'history': player_data['history'],
        }
