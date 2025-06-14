#!/usr/bin/env python3
"""
Ace Pot Manager

This module provides functionality for managing the ace pot tracker.
"""

import datetime
from typing import Dict, List, Optional, Any
from .tournament_db_manager import TournamentDBManager


class AcePotManager:
    def __init__(self, db_manager: TournamentDBManager):
        """Initialize the ace pot manager."""
        self.db_manager = db_manager
        
    def get_balance(self) -> Dict[str, float]:
        """
        Get the current ace pot balance.
        
        Returns:
            Dictionary with total, current, and reserve balances
        """
        return self.db_manager.get_ace_pot_balance()
        
    def get_config(self) -> Dict[str, float]:
        """
        Get the ace pot configuration.
        
        Returns:
            Dictionary with ace pot configuration
        """
        config = self.db_manager.get_ace_pot_config()
        if not config:
            return {'cap_amount': 100.0}  # Default value
        return config
        
    def update_config(self, cap_amount: float) -> bool:
        """
        Update the ace pot configuration.
        
        Args:
            cap_amount: The cap amount for the current ace pot
            
        Returns:
            True if successful, False otherwise
        """
        return self.db_manager.update_ace_pot_config(cap_amount)
        
    def get_ledger(self) -> List[Dict[str, Any]]:
        """
        Get the ace pot ledger.
        
        Returns:
            List of ace pot entries
        """
        return self.db_manager.get_ace_pot_ledger()
        
    def add_entry(self, description: str, amount: float, date: str = None,
                 tournament_id: int = None, player_name: str = None) -> int:
        """
        Add an entry to the ace pot tracker.
        
        Args:
            description: Entry description
            amount: Amount to add/subtract from the pot
            date: Optional entry date (defaults to today)
            tournament_id: Optional tournament ID
            player_name: Optional player name
            
        Returns:
            Entry ID
        """
        if date is None:
            date = datetime.datetime.now().strftime("%Y-%m-%d")
            
        player_id = None
        if player_name:
            try:
                player_id = self.db_manager._get_player_id_safe(player_name)
            except:
                pass
                
        return self.db_manager.add_ace_pot_entry(
            date=date,
            description=description,
            amount=amount,
            tournament_id=tournament_id,
            player_id=player_id
        )
        
    def set_balance(self, amount: float, description: str = None) -> bool:
        """
        Set the ace pot balance to a specific amount.
        
        Args:
            amount: New balance amount
            description: Optional description for the entry
            
        Returns:
            True if successful, False otherwise
        """
        if description is None:
            description = "Manual balance adjustment"
            
        return self.db_manager.set_ace_pot_balance(amount, description=description)
        
    def process_payout(self, tournament_id: int, player_name: str) -> bool:
        """
        Process an ace pot payout for a tournament.
        
        Args:
            tournament_id: Tournament ID
            player_name: Player who hit the ace
            
        Returns:
            True if successful, False otherwise
        """
        return self.db_manager.process_ace_pot_payout(tournament_id, player_name)
        
    def add_participant_buy_in(self, tournament_id: int, player_name: str) -> bool:
        """
        Add a participant buy-in to the ace pot.
        
        Args:
            tournament_id: Tournament ID
            player_name: Player name
            
        Returns:
            True if successful, False otherwise
        """
        participant_id = self.db_manager.add_tournament_participant(
            tournament_id=tournament_id,
            player_name=player_name,
            ace_pot_buy_in=True
        )
        
        return participant_id is not None
