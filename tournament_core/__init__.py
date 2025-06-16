"""
Disc Golf League Tournament Rating System

A rating system for doubles disc golf leagues that tracks individual player contributions
and predicts team performance in tournament-style play.
"""

from .tournament_ratings import TournamentRatingSystem
from .tournament_db_manager import TournamentDBManager
from .db_migration import migrate_database

# Run database migrations automatically when the package is imported
try:
    migrate_database()
except Exception as e:
    print(f"Warning: Database migration failed: {e}")
    print("You may need to run migrations manually.")

__version__ = '1.0.0'
