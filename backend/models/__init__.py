"""Unified model registry.

Imports all models so SQLAlchemy discovers them when db.create_all() is called.
Other modules should import from here:

    from backend.models import db, User, Player, TagMember, ...
"""

# Platform (shared)
from .platform import db, User, UserSession, PiiAccessLog  # noqa: F401

# DG-Dubs
from .dubs import (  # noqa: F401
    Player, Tournament, Team, PlayerHistory,
    TournamentParticipant, AcePotTracker, AcePotConfig, Season,
)

# DG-Tags
from .tags import (  # noqa: F401
    TagMember, MemberContactInfo, TagEvent, TagRegistration, TagHistory,
    TagInventory, TagUnavailable,
)
