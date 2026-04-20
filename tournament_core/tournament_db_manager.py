#!/usr/bin/env python3
"""
Tournament Database Manager

This module provides MySQL/SQLAlchemy database functionality for the tournament rating system.
It handles all CRUD operations using the shared Flask-SQLAlchemy models.
"""

import datetime
from typing import Dict, List, Optional, Any

from .models import (
    db, Player, Tournament, Team, PlayerHistory,
    TournamentParticipant, AcePotTracker, AcePotConfig
)


class TournamentDBManager:
    """Database manager using Flask-SQLAlchemy for MySQL."""

    def __init__(self):
        """Initialize the database manager. Requires Flask app context."""
        pass

    # ── Players ──────────────────────────────────────────────────────

    def add_player(self, name: str, rating: float, is_club_member: bool = False) -> int:
        player = Player(name=name, rating=rating, tournaments_played=0, is_club_member=is_club_member)
        db.session.add(player)
        db.session.commit()
        return player.player_id

    def update_player_rating(self, name: str, rating: float) -> bool:
        player = Player.query.filter(db.func.lower(Player.name) == name.lower()).first()
        if not player:
            return False
        player.rating = rating
        db.session.commit()
        return True

    def increment_player_tournaments(self, name: str) -> bool:
        player = Player.query.filter(db.func.lower(Player.name) == name.lower()).first()
        if not player:
            return False
        player.tournaments_played += 1
        db.session.commit()
        return True

    def get_player_id(self, name: str) -> int:
        player = Player.query.filter(db.func.lower(Player.name) == name.lower()).first()
        if not player:
            raise ValueError(f"Player not found: {name}")
        return player.player_id

    def get_all_players(self) -> List[Dict[str, Any]]:
        players = Player.query.order_by(Player.rating.desc()).all()
        return [
            {
                'id': p.player_id,
                'name': p.name,
                'rating': float(p.rating),
                'tournaments_played': p.tournaments_played,
                'is_club_member': p.is_club_member,
            }
            for p in players
        ]

    def update_player_club_membership(self, player_name: str, is_club_member: bool) -> bool:
        player = Player.query.filter(db.func.lower(Player.name) == player_name.lower()).first()
        if not player:
            return False
        player.is_club_member = is_club_member
        db.session.commit()
        return True

    # ── Tournaments ──────────────────────────────────────────────────

    def add_tournament(self, date: str, course: str, team_count: int, ace_pot_paid: bool = False) -> Optional[int]:
        t = Tournament(date=date, course=course, team_count=team_count, ace_pot_paid=ace_pot_paid)
        db.session.add(t)
        db.session.commit()
        return t.tournament_id

    def get_tournaments(self) -> List[Dict[str, Any]]:
        tournaments = Tournament.query.order_by(Tournament.date.desc()).all()
        result = []
        for t in tournaments:
            td = {
                'id': t.tournament_id,
                'date': t.date.isoformat() if hasattr(t.date, 'isoformat') else str(t.date),
                'course': t.course,
                'team_count': t.team_count,
                'status': t.status or 'Completed',
                'ace_pot_paid': t.ace_pot_paid,
                'results': [],
            }
            teams = Team.query.filter_by(tournament_id=t.tournament_id).order_by(Team.position).all()
            for team in teams:
                p1 = Player.query.get(team.player1_id)
                p2 = Player.query.get(team.player2_id) if team.player2_id else None
                td['results'].append({
                    'player1_name': p1.name if p1 else 'Unknown',
                    'player2_name': p2.name if p2 else 'Ghost Player',
                    'position': team.position,
                    'expected_position': float(team.expected_position),
                    'score': team.score,
                    'team_rating': float(team.team_rating),
                    'payout': float(team.payout) if team.payout else 0,
                })
            result.append(td)
        return result

    # ── Teams ────────────────────────────────────────────────────────

    def add_team_result(self, tournament_id: int, player1: str, player2: str,
                        position: int, expected_position: float,
                        score: int, team_rating: float) -> Optional[int]:
        p1_id = self._get_player_id_safe(player1)
        p2_id = self._get_player_id_safe(player2) if player2 != "Ghost Player" else None

        if p1_id is None and player1 != "Ghost Player":
            print(f"Error: Player {player1} not found")
            return None

        team = Team(
            tournament_id=tournament_id,
            player1_id=p1_id,
            player2_id=p2_id,
            is_ghost_team=(p2_id is None),
            position=position,
            expected_position=expected_position,
            score=score,
            team_rating=team_rating,
        )
        db.session.add(team)
        db.session.commit()
        return team.team_id

    # ── Player History ───────────────────────────────────────────────

    def add_player_history(self, player_name: str, tournament_id: int,
                           old_rating: float, new_rating: float,
                           position: int, expected_position: float,
                           score: int, with_ghost: bool) -> Optional[int]:
        player_id = self._get_player_id_safe(player_name)
        if player_id is None:
            print(f"Error: Player {player_name} not found")
            return None

        ph = PlayerHistory(
            player_id=player_id,
            tournament_id=tournament_id,
            old_rating=old_rating,
            new_rating=new_rating,
            position=position,
            expected_position=expected_position,
            score=score,
            with_ghost=with_ghost,
        )
        db.session.add(ph)
        db.session.commit()
        return ph.history_id

    def get_player_history(self, player_name: str) -> List[Dict[str, Any]]:
        player = Player.query.filter(db.func.lower(Player.name) == player_name.lower()).first()
        if not player:
            return []

        rows = (
            db.session.query(PlayerHistory, Tournament.date)
            .join(Tournament, PlayerHistory.tournament_id == Tournament.tournament_id)
            .filter(PlayerHistory.player_id == player.player_id)
            .order_by(Tournament.date.desc())
            .all()
        )
        return [
            {
                'tournament_date': row.date.isoformat() if hasattr(row.date, 'isoformat') else str(row.date),
                'old_rating': float(ph.old_rating),
                'new_rating': float(ph.new_rating),
                'position': ph.position,
                'expected_position': float(ph.expected_position),
                'score': ph.score,
                'with_ghost': ph.with_ghost,
            }
            for ph, _ in rows
            for row in [type('R', (), {'date': _})]
        ]

    # ── Ace Pot ──────────────────────────────────────────────────────

    def get_ace_pot_config(self) -> Dict[str, float]:
        config = AcePotConfig.query.get(1)
        return {'cap_amount': float(config.cap_amount)} if config else {'cap_amount': 100.0}

    def update_ace_pot_config(self, cap_amount: float) -> bool:
        config = AcePotConfig.query.get(1)
        if config:
            config.cap_amount = cap_amount
        else:
            config = AcePotConfig(id=1, cap_amount=cap_amount)
            db.session.add(config)
        db.session.commit()
        return True

    def get_ace_pot_balance(self) -> Dict[str, float]:
        latest = AcePotTracker.query.order_by(AcePotTracker.entry_id.desc()).first()
        total = float(latest.balance) if latest else 0.0
        cap = self.get_ace_pot_config()['cap_amount']
        return {
            'total': total,
            'current': min(total, cap),
            'reserve': max(0, total - cap),
        }

    def add_ace_pot_entry(self, date: str, description: str, amount: float,
                          tournament_id: int = None, player_id: int = None) -> Optional[int]:
        latest = AcePotTracker.query.order_by(AcePotTracker.entry_id.desc()).first()
        current_balance = float(latest.balance) if latest else 0.0
        new_balance = current_balance + amount

        entry = AcePotTracker(
            date=date, description=description, amount=amount,
            balance=new_balance, tournament_id=tournament_id, player_id=player_id,
        )
        db.session.add(entry)
        db.session.commit()
        return entry.entry_id

    def get_ace_pot_ledger(self) -> List[Dict[str, Any]]:
        rows = (
            db.session.query(AcePotTracker, Tournament.date, Tournament.course, Player.name)
            .outerjoin(Tournament, AcePotTracker.tournament_id == Tournament.tournament_id)
            .outerjoin(Player, AcePotTracker.player_id == Player.player_id)
            .order_by(AcePotTracker.entry_id.desc())
            .all()
        )
        return [
            {
                'id': e.entry_id,
                'date': e.date.isoformat() if hasattr(e.date, 'isoformat') else str(e.date),
                'description': e.description,
                'amount': float(e.amount),
                'balance': float(e.balance),
                'tournament_id': e.tournament_id,
                'tournament_date': t_date.isoformat() if t_date and hasattr(t_date, 'isoformat') else str(t_date) if t_date else None,
                'course': t_course,
                'player_name': p_name,
                'player_id': e.player_id,
            }
            for e, t_date, t_course, p_name in rows
        ]

    def set_ace_pot_balance(self, amount: float, date: str = None, description: str = None) -> bool:
        latest = AcePotTracker.query.order_by(AcePotTracker.entry_id.desc()).first()
        current = float(latest.balance) if latest else 0.0
        adjustment = amount - current
        if date is None:
            date = datetime.datetime.now().strftime("%Y-%m-%d")
        if description is None:
            description = "Manual balance adjustment"

        entry = AcePotTracker(date=date, description=description, amount=adjustment, balance=amount)
        db.session.add(entry)
        db.session.commit()
        return True

    def process_ace_pot_payout(self, tournament_id: int, player_name: str) -> bool:
        player = Player.query.filter(db.func.lower(Player.name) == player_name.lower()).first()
        if not player:
            return False

        t = Tournament.query.get(tournament_id)
        t_date = t.date.isoformat() if t and hasattr(t.date, 'isoformat') else datetime.datetime.now().strftime("%Y-%m-%d")

        balance = self.get_ace_pot_balance()
        payout = -balance['current']

        self.add_ace_pot_entry(
            date=t_date,
            description=f"Ace pot payout to {player_name}",
            amount=payout,
            tournament_id=tournament_id,
            player_id=player.player_id,
        )

        t.ace_pot_paid = True
        t.ace_pot_paid_to = player_name
        db.session.commit()
        return True

    # ── Tournament Participants ──────────────────────────────────────

    def add_tournament_participant(self, tournament_id: int, player_name: str,
                                   ace_pot_buy_in: bool = False,
                                   skip_ace_pot_entry: bool = False) -> Optional[int]:
        player_id = self._get_player_id_safe(player_name)
        if player_id is None or player_id == -1:
            return None

        existing = TournamentParticipant.query.filter_by(
            tournament_id=tournament_id, player_id=player_id
        ).first()

        if existing:
            existing.ace_pot_buy_in = ace_pot_buy_in
            db.session.commit()
            return existing.participant_id

        tp = TournamentParticipant(
            tournament_id=tournament_id, player_id=player_id, ace_pot_buy_in=ace_pot_buy_in
        )
        db.session.add(tp)
        db.session.commit()

        if ace_pot_buy_in and not skip_ace_pot_entry:
            t = Tournament.query.get(tournament_id)
            t_date = t.date.isoformat() if t and hasattr(t.date, 'isoformat') else datetime.datetime.now().strftime("%Y-%m-%d")
            self.add_ace_pot_entry(
                date=t_date,
                description=f"Ace pot buy-in: {player_name}",
                amount=1.0,
                tournament_id=tournament_id,
                player_id=player_id,
            )

        return tp.participant_id

    def get_tournament_participants(self, tournament_id: int) -> List[Dict[str, Any]]:
        rows = (
            db.session.query(TournamentParticipant, Player)
            .join(Player, TournamentParticipant.player_id == Player.player_id)
            .filter(TournamentParticipant.tournament_id == tournament_id)
            .order_by(Player.name)
            .all()
        )
        return [
            {
                'id': tp.participant_id,
                'tournament_id': tp.tournament_id,
                'player_id': tp.player_id,
                'ace_pot_buy_in': tp.ace_pot_buy_in,
                'name': p.name,
                'rating': float(p.rating),
                'is_club_member': p.is_club_member,
            }
            for tp, p in rows
        ]

    # ── Helpers ──────────────────────────────────────────────────────

    def _get_player_id_safe(self, name: str) -> Optional[int]:
        if name == "Ghost Player":
            return -1
        player = Player.query.filter(db.func.lower(Player.name) == name.lower()).first()
        return player.player_id if player else None

    def commit_transaction(self):
        db.session.commit()
