"""
API module for the Disc Golf League Tournament Rating System.
"""

from .players import players_bp
from .tournaments import tournaments_bp
from .storage import storage_bp
from .auth import auth_api_bp
from .ace_pot import ace_pot_bp
from .archive import archive_bp

all_blueprints = [players_bp, tournaments_bp, storage_bp, auth_api_bp, ace_pot_bp, archive_bp]
