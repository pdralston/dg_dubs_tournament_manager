"""DG-Putt API route blueprints.

All mounted under url_prefix='/api/putt'. Auth is the shared two-axis model:
require_role(app='putt', role=...). Public reads (lists, standings, matches,
ace-pot) carry no decorator.
"""

from .players import players_bp
from .tournaments import tournaments_bp
from .matches import matches_bp
from .tournament_edit import tournament_edit_bp
from .admin_audit import admin_audit_bp
from .ace_pot import ace_pot_bp
from .archive import archive_bp

putt_blueprints = [
    players_bp,
    tournaments_bp,
    matches_bp,
    tournament_edit_bp,
    admin_audit_bp,
    ace_pot_bp,
    archive_bp,
]
