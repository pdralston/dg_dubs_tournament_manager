#!/usr/bin/env python3
"""
Ace Pot Manager

This module provides functionality for managing the ace pot tracker.
"""

import datetime
from typing import Dict, List, Any
from .tournament_db_manager import TournamentDBManager
from .models import Tournament


class AcePotManager:
    def __init__(self, db_manager: TournamentDBManager):
        self.db_manager = db_manager

    def get_balance(self) -> Dict[str, float]:
        return self.db_manager.get_ace_pot_balance()

    def get_config(self) -> Dict[str, float]:
        config = self.db_manager.get_ace_pot_config()
        return config if config else {'cap_amount': 100.0}

    def update_config(self, cap_amount: float) -> bool:
        return self.db_manager.update_ace_pot_config(cap_amount)

    def get_ledger(self) -> List[Dict[str, Any]]:
        return self.db_manager.get_ace_pot_ledger()

    def add_entry(self, description: str, amount: float, date: str = None,
                  tournament_id: int = None, player_name: str = None) -> int:
        if date is None:
            date = datetime.datetime.now().strftime("%Y-%m-%d")
        player_id = None
        if player_name:
            player_id = self.db_manager._get_player_id_safe(player_name)
        return self.db_manager.add_ace_pot_entry(
            date=date, description=description, amount=amount,
            tournament_id=tournament_id, player_id=player_id,
        )

    def set_balance(self, amount: float, description: str = None) -> bool:
        if description is None:
            description = "Manual balance adjustment"
        return self.db_manager.set_ace_pot_balance(amount, description=description)

    def process_payout(self, tournament_id: int, player_name: str) -> bool:
        return self.db_manager.process_ace_pot_payout(tournament_id, player_name)

    def add_participant_buy_in(self, tournament_id: int, player_name: str) -> bool:
        pid = self.db_manager.add_tournament_participant(
            tournament_id=tournament_id, player_name=player_name, ace_pot_buy_in=True,
        )
        return pid is not None

    def process_batch_buy_ins(self, tournament_id: int, player_names: List[str]) -> Dict[str, Any]:
        if not player_names:
            return {'success': 0, 'failure': 0, 'amount': 0.0}

        t = Tournament.query.get(tournament_id)
        tournament_date = t.date.isoformat() if t and hasattr(t.date, 'isoformat') else datetime.datetime.now().strftime("%Y-%m-%d")

        amount = len(player_names) * 1.0
        entry_id = self.add_entry(
            description=f"Ace pot buy-ins: {len(player_names)} players",
            amount=amount, date=tournament_date, tournament_id=tournament_id,
        )

        success_count = 0
        failure_count = 0
        for name in player_names:
            try:
                pid = self.db_manager.add_tournament_participant(
                    tournament_id=tournament_id, player_name=name,
                    ace_pot_buy_in=True, skip_ace_pot_entry=True,
                )
                if pid is not None:
                    success_count += 1
                else:
                    failure_count += 1
            except Exception as e:
                print(f"Error adding participant {name}: {e}")
                failure_count += 1

        return {'success': success_count, 'failure': failure_count, 'amount': amount, 'entry_id': entry_id}
