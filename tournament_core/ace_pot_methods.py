#!/usr/bin/env python3
"""
Ace Pot Methods

This module contains the Ace Pot related methods for the TournamentDBManager class.
"""

import sqlite3
import datetime
from typing import Dict, List, Any

def get_ace_pot_config(self) -> Dict[str, float]:
    """
    Get the ace pot configuration.
    
    Returns:
        Dictionary with ace pot configuration
    """
    config = {'cap_amount': 100.0}  # Default value
    try:
        self.connect()
        if not self.conn:
            print("Warning: Database connection failed in get_ace_pot_config")
            return config
            
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM ace_pot_config WHERE id = 1")
        result = cursor.fetchone()
        
        if result:
            config = {'cap_amount': result['cap_amount']}
    except sqlite3.Error as e:
        print(f"Error getting ace pot config: {e}")
    finally:
        self.close()
        return config
        
def update_ace_pot_config(self, cap_amount: float) -> bool:
    """
    Update the ace pot configuration.
    
    Args:
        cap_amount: The cap amount for the current ace pot
        
    Returns:
        True if successful, False otherwise
    """
    success = False
    try:
        self.connect()
        if not self.conn:
            print("Warning: Database connection failed in update_ace_pot_config")
            return success
            
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE ace_pot_config SET cap_amount = ? WHERE id = 1",
            (cap_amount,)
        )
        
        # If no rows were updated, insert a new record
        if cursor.rowcount == 0:
            cursor.execute(
                "INSERT OR REPLACE INTO ace_pot_config (id, cap_amount) VALUES (1, ?)",
                (cap_amount,)
            )
            
        self.conn.commit()
        success = True
    except sqlite3.Error as e:
        print(f"Error updating ace pot config: {e}")
        if self.conn:
            try:
                self.conn.rollback()
            except:
                pass
    finally:
        self.close()
        return success
        
def get_ace_pot_balance(self) -> Dict[str, float]:
    """
    Get the current ace pot balance.
    
    Returns:
        Dictionary with total, current, and reserve balances
    """
    try:
        self.connect()
        if not self.conn:
            print("Warning: Database connection failed in get_ace_pot_balance")
            return {'total': 0.0, 'current': 0.0, 'reserve': 0.0}
            
        cursor = self.conn.cursor()
        
        # Get the latest balance
        cursor.execute(
            "SELECT balance FROM ace_pot_tracker ORDER BY id DESC LIMIT 1"
        )
        result = cursor.fetchone()
        
        total_balance = result['balance'] if result else 0.0
        
        # Get the cap amount
        config = self.get_ace_pot_config()
        cap_amount = config['cap_amount']
        
        # Calculate current and reserve balances
        current_balance = min(total_balance, cap_amount)
        reserve_balance = max(0, total_balance - cap_amount)
        
        return {
            'total': total_balance,
            'current': current_balance,
            'reserve': reserve_balance
        }
    except sqlite3.Error as e:
        print(f"Error getting ace pot balance: {e}")
        return {'total': 0.0, 'current': 0.0, 'reserve': 0.0}
    finally:
        self.close()
        
def add_ace_pot_entry(self, date: str, description: str, amount: float, 
                     tournament_id: int = None, player_id: int = None) -> int:
    """
    Add an entry to the ace pot tracker.
    
    Args:
        date: Entry date
        description: Entry description
        amount: Amount to add/subtract from the pot
        tournament_id: Optional tournament ID
        player_id: Optional player ID
        
    Returns:
        Entry ID
    """
    entry_id = None
    try:
        self.connect()
        if not self.conn:
            print("Warning: Database connection failed in add_ace_pot_entry")
            return entry_id
            
        cursor = self.conn.cursor()
        
        # Get current balance
        cursor.execute(
            "SELECT balance FROM ace_pot_tracker ORDER BY id DESC LIMIT 1"
        )
        result = cursor.fetchone()
        
        current_balance = result['balance'] if result else 0.0
        new_balance = current_balance + amount
        
        # Add entry
        cursor.execute(
            """INSERT INTO ace_pot_tracker 
               (date, description, amount, balance, tournament_id, player_id)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (date, description, amount, new_balance, tournament_id, player_id)
        )
        
        entry_id = cursor.lastrowid
        self.conn.commit()
    except sqlite3.Error as e:
        print(f"Error adding ace pot entry: {e}")
        if self.conn:
            try:
                self.conn.rollback()
            except:
                pass
    finally:
        self.close()
        return entry_id
        
def get_ace_pot_ledger(self) -> List[Dict[str, Any]]:
    """
    Get the ace pot ledger.
    
    Returns:
        List of ace pot entries
    """
    entries = []
    try:
        self.connect()
        if not self.conn:
            print("Warning: Database connection failed in get_ace_pot_ledger")
            return entries
            
        cursor = self.conn.cursor()
        cursor.execute(
            """SELECT apt.*, t.date as tournament_date, t.course, p.name as player_name
               FROM ace_pot_tracker apt
               LEFT JOIN tournaments t ON apt.tournament_id = t.id
               LEFT JOIN players p ON apt.player_id = p.id
               ORDER BY apt.id DESC"""
        )
        
        entries = [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        print(f"Error getting ace pot ledger: {e}")
    finally:
        self.close()
        return entries
        
def add_tournament_participant(self, tournament_id: int, player_name: str, ace_pot_buy_in: bool = False, skip_ace_pot_entry: bool = False) -> int:
    """
    Add a participant to a tournament.
    
    Args:
        tournament_id: Tournament ID
        player_name: Player name
        ace_pot_buy_in: Whether the player bought into the ace pot
        skip_ace_pot_entry: Whether to skip adding an ace pot entry (for batch processing)
        
    Returns:
        Participant ID
    """
    participant_id = None
    try:
        self.connect()
        if not self.conn:
            print("Warning: Database connection failed in add_tournament_participant")
            return participant_id
            
        cursor = self.conn.cursor()
        
        # Get player ID
        player_id = self._get_player_id_safe(player_name)
        if player_id is None or player_id == -1:  # -1 is ghost player
            print(f"Warning: Player {player_name} not found, skipping participant")
            return participant_id
            
        # Add participant
        cursor.execute(
            """INSERT INTO tournament_participants
               (tournament_id, player_id, ace_pot_buy_in)
               VALUES (?, ?, ?)""",
            (tournament_id, player_id, ace_pot_buy_in)
        )
        
        participant_id = cursor.lastrowid
        self.conn.commit()
        
        # If player bought into ace pot and we're not skipping the entry, add entry to ace pot tracker
        if ace_pot_buy_in and not skip_ace_pot_entry:
            # Get tournament date
            cursor.execute(
                "SELECT date FROM tournaments WHERE id = ?",
                (tournament_id,)
            )
            result = cursor.fetchone()
            tournament_date = result['date'] if result else datetime.datetime.now().strftime("%Y-%m-%d")
            
            # Add ace pot entry
            self.add_ace_pot_entry(
                date=tournament_date,
                description=f"Ace pot buy-in: {player_name}",
                amount=1.0,  # $1 per player
                tournament_id=tournament_id,
                player_id=player_id
            )
    except sqlite3.IntegrityError:
        # Participant already exists, update ace pot buy-in
        self.conn.execute(
            """UPDATE tournament_participants
               SET ace_pot_buy_in = ?
               WHERE tournament_id = ? AND player_id = ?""",
            (ace_pot_buy_in, tournament_id, player_id)
        )
        self.conn.commit()
        
        # Get participant ID
        cursor.execute(
            """SELECT id FROM tournament_participants
               WHERE tournament_id = ? AND player_id = ?""",
            (tournament_id, player_id)
        )
        result = cursor.fetchone()
        participant_id = result['id'] if result else None
    except sqlite3.Error as e:
        print(f"Error adding tournament participant: {e}")
        if self.conn:
            try:
                self.conn.rollback()
            except:
                pass
    finally:
        self.close()
        return participant_id
        
def get_tournament_participants(self, tournament_id: int) -> List[Dict[str, Any]]:
    """
    Get participants for a tournament.
    
    Args:
        tournament_id: Tournament ID
        
    Returns:
        List of participant dictionaries
    """
    participants = []
    try:
        self.connect()
        if not self.conn:
            print("Warning: Database connection failed in get_tournament_participants")
            return participants
            
        cursor = self.conn.cursor()
        cursor.execute(
            """SELECT tp.*, p.name, p.rating, p.is_club_member
               FROM tournament_participants tp
               JOIN players p ON tp.player_id = p.id
               WHERE tp.tournament_id = ?
               ORDER BY p.name""",
            (tournament_id,)
        )
        
        participants = [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        print(f"Error getting tournament participants: {e}")
    finally:
        self.close()
        return participants
        
def update_player_club_membership(self, player_name: str, is_club_member: bool) -> bool:
    """
    Update a player's club membership status.
    
    Args:
        player_name: Player name
        is_club_member: Whether the player is a club member
        
    Returns:
        True if successful, False otherwise
    """
    success = False
    try:
        self.connect()
        if not self.conn:
            print("Warning: Database connection failed in update_player_club_membership")
            return success
            
        # Check if is_club_member column exists
        cursor = self.conn.cursor()
        cursor.execute("PRAGMA table_info(players)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'is_club_member' in columns:
            cursor.execute(
                "UPDATE players SET is_club_member = ? WHERE name = ?",
                (is_club_member, player_name)
            )
            self.conn.commit()
            success = True
        else:
            # Column doesn't exist, but we'll consider this a success
            # since we're just storing this in memory for now
            print("Note: is_club_member column doesn't exist in players table. Skipping database update.")
            success = True
    except sqlite3.Error as e:
        print(f"Error updating player club membership: {e}")
        if self.conn:
            try:
                self.conn.rollback()
            except:
                pass
    finally:
        self.close()
        return success
        
def set_ace_pot_balance(self, amount: float, date: str = None, description: str = None) -> bool:
    """
    Set the ace pot balance to a specific amount.
    
    Args:
        amount: New balance amount
        date: Optional date for the entry
        description: Optional description for the entry
        
    Returns:
        True if successful, False otherwise
    """
    success = False
    try:
        self.connect()
        if not self.conn:
            print("Warning: Database connection failed in set_ace_pot_balance")
            return success
            
        # Get current balance
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT balance FROM ace_pot_tracker ORDER BY id DESC LIMIT 1"
        )
        result = cursor.fetchone()
        
        current_balance = result['balance'] if result else 0.0
        adjustment_amount = amount - current_balance
        
        # Use current date if not provided
        if date is None:
            date = datetime.datetime.now().strftime("%Y-%m-%d")
            
        # Use default description if not provided
        if description is None:
            description = "Manual balance adjustment"
            
        # Add entry
        cursor.execute(
            """INSERT INTO ace_pot_tracker 
               (date, description, amount, balance)
               VALUES (?, ?, ?, ?)""",
            (date, description, adjustment_amount, amount)
        )
        
        self.conn.commit()
        success = True
    except sqlite3.Error as e:
        print(f"Error setting ace pot balance: {e}")
        if self.conn:
            try:
                self.conn.rollback()
            except:
                pass
    finally:
        self.close()
        return success
        
def process_ace_pot_payout(self, tournament_id: int, player_name: str) -> bool:
    """
    Process an ace pot payout for a tournament.
    
    Args:
        tournament_id: Tournament ID
        player_name: Player who hit the ace
        
    Returns:
        True if successful, False otherwise
    """
    success = False
    try:
        self.connect()
        if not self.conn:
            print("Warning: Database connection failed in process_ace_pot_payout")
            return success
            
        # Get player ID
        player_id = self._get_player_id_safe(player_name)
        if player_id is None:
            print(f"Warning: Player {player_name} not found, skipping payout")
            return success
            
        # Get tournament date
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT date FROM tournaments WHERE id = ?",
            (tournament_id,)
        )
        result = cursor.fetchone()
        tournament_date = result['date'] if result else datetime.datetime.now().strftime("%Y-%m-%d")
        
        # Get current ace pot balance
        ace_pot_balance = self.get_ace_pot_balance()
        payout_amount = -ace_pot_balance['current']  # Negative because it's a payout
        
        # Add ace pot entry
        self.add_ace_pot_entry(
            date=tournament_date,
            description=f"Ace pot payout to {player_name}",
            amount=payout_amount,
            tournament_id=tournament_id,
            player_id=player_id
        )
        
        # Update tournament record
        cursor.execute(
            "UPDATE tournaments SET ace_pot_paid = 1, ace_pot_paid_to = ? WHERE id = ?",
            (player_id, tournament_id)
        )
        
        self.conn.commit()
        success = True
    except sqlite3.Error as e:
        print(f"Error processing ace pot payout: {e}")
        if self.conn:
            try:
                self.conn.rollback()
            except:
                pass
    finally:
        self.close()
        return success
