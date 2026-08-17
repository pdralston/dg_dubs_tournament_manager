"""DG-Dubs API route blueprints."""

from .players import players_bp
from .tournaments import tournaments_bp
from .ace_pot import ace_pot_bp
from .archive import archive_bp
from .auth_api import auth_api_bp
from .storage import storage_bp

dubs_blueprints = [players_bp, tournaments_bp, ace_pot_bp, archive_bp, auth_api_bp, storage_bp]
