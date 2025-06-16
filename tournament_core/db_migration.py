#!/usr/bin/env python3
"""
Database Migration Script

This script handles database schema migrations for the tournament rating system.
"""

import sqlite3
import os
import sys

def migrate_database(db_file="tournament_data.db"):
    """
    Perform all necessary database migrations.
    
    Args:
        db_file: Path to the database file
    """
    print(f"Checking database schema for {db_file}...")
    
    # Check if database file exists
    if not os.path.exists(db_file):
        print(f"Database file {db_file} not found.")
        return
    
    # Connect to database
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        # Migration 1: Add ace_pot_paid column to tournaments table
        add_ace_pot_paid_column(conn, cursor)
        
        # Close connection
        conn.commit()
        conn.close()
        print("Database migration completed successfully.")
    except sqlite3.Error as e:
        print(f"Error during database migration: {e}")
        if conn:
            conn.close()
        sys.exit(1)

def add_ace_pot_paid_column(conn, cursor):
    """
    Add ace_pot_paid column to tournaments table if it doesn't exist.
    
    Args:
        conn: Database connection
        cursor: Database cursor
    """
    try:
        # Check if column exists
        cursor.execute("PRAGMA table_info(tournaments)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'ace_pot_paid' not in columns:
            print("Adding ace_pot_paid column to tournaments table...")
            cursor.execute("ALTER TABLE tournaments ADD COLUMN ace_pot_paid BOOLEAN NOT NULL DEFAULT 0")
            conn.commit()
            print("Column added successfully")
        else:
            print("ace_pot_paid column already exists")
    except sqlite3.Error as e:
        print(f"Error adding ace_pot_paid column: {e}")
        conn.rollback()
        raise

if __name__ == "__main__":
    # Run migration when script is executed directly
    migrate_database()
