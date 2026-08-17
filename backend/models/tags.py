"""DG-Tags domain models.

Bag tag tracking system: members, events, registrations,
tag distribution history, inventory management, and PII contact info.
"""

from datetime import datetime
from .platform import db


class TagMember(db.Model):
    """A member of the bag tag club/organization."""
    __tablename__ = 'tag_members'

    member_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    udisc_name = db.Column(db.String(100), nullable=True)
    current_tag = db.Column(db.Integer, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)

    contact_info = db.relationship(
        'MemberContactInfo', backref='member', uselist=False,
        cascade='all, delete-orphan'
    )
    registrations = db.relationship('TagRegistration', backref='member', lazy='dynamic')
    tag_history = db.relationship('TagHistory', backref='member', lazy='dynamic')


class MemberContactInfo(db.Model):
    """PII table — write access for Directors, read access for Admins only."""
    __tablename__ = 'member_contact_info'

    member_id = db.Column(
        db.Integer,
        db.ForeignKey('tag_members.member_id', ondelete='CASCADE'),
        primary_key=True
    )
    email = db.Column(db.String(255), nullable=True)
    phone = db.Column(db.String(50), nullable=True)
    shipping_address = db.Column(db.Text, nullable=True)
    payment_method = db.Column(db.String(50), nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TagEvent(db.Model):
    """A bag tag event (annual or monthly)."""
    __tablename__ = 'tag_events'

    event_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    event_type = db.Column(
        db.Enum('annual', 'monthly', name='event_type_enum'),
        nullable=False
    )
    date = db.Column(db.Date, nullable=False)
    course = db.Column(db.String(200), nullable=True)
    status = db.Column(
        db.Enum('pending', 'scheduled', 'in_progress', 'complete', name='event_status_enum'),
        default='pending'
    )
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    registrations = db.relationship('TagRegistration', backref='event', lazy='dynamic')
    history_entries = db.relationship('TagHistory', backref='event', lazy='dynamic')

    # Valid status transitions
    VALID_TRANSITIONS = {
        'pending': ['scheduled'],
        'scheduled': ['in_progress'],
        'in_progress': ['complete'],
        'complete': [],
    }

    def can_transition_to(self, new_status: str) -> bool:
        """Check if a status transition is valid."""
        return new_status in self.VALID_TRANSITIONS.get(self.status, [])


class TagRegistration(db.Model):
    """A player/non-player registration for an event."""
    __tablename__ = 'tag_registrations'

    reg_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    event_id = db.Column(db.Integer, db.ForeignKey('tag_events.event_id'), nullable=False)
    member_id = db.Column(db.Integer, db.ForeignKey('tag_members.member_id'), nullable=False)
    is_player = db.Column(db.Boolean, default=True)
    is_checked_in = db.Column(db.Boolean, default=False)
    is_dnf = db.Column(db.Boolean, default=False)
    old_tag = db.Column(db.Integer, nullable=True)
    round_score = db.Column(db.Integer, nullable=True)
    new_tag = db.Column(db.Integer, nullable=True)
    position = db.Column(db.Integer, nullable=True)

    __table_args__ = (
        db.UniqueConstraint('event_id', 'member_id', name='uq_tag_event_member'),
    )


class TagHistory(db.Model):
    """Historical record of tag assignments from finalized events."""
    __tablename__ = 'tag_history'

    history_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    member_id = db.Column(db.Integer, db.ForeignKey('tag_members.member_id'), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('tag_events.event_id'), nullable=False)
    old_tag = db.Column(db.Integer, nullable=True)
    new_tag = db.Column(db.Integer, nullable=False)
    round_score = db.Column(db.Integer, nullable=True)
    is_dnf = db.Column(db.Boolean, default=False)
    position = db.Column(db.Integer, nullable=True)


class TagInventory(db.Model):
    """Organization-level tag inventory for a season (year)."""
    __tablename__ = 'tag_inventory'

    inventory_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    season_year = db.Column(db.Integer, nullable=False, unique=True)
    total_tags = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TagUnavailable(db.Model):
    """Individual tag numbers that have been removed from circulation."""
    __tablename__ = 'tag_unavailable'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    season_year = db.Column(db.Integer, nullable=False)
    tag_number = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('season_year', 'tag_number', name='uq_season_tag_unavailable'),
    )
