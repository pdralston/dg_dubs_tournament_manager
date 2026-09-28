"""Platform-level models shared across all apps.

Includes authentication (User, UserSession) and audit logging (PiiAccessLog).
"""

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import declared_attr

db = SQLAlchemy()


class Organization(db.Model):
    """A tenant organization. All domain data is scoped to an org.

    Phase 1 seeds a single org (SVDGC); the model is multi-org ready.
    """
    __tablename__ = 'organizations'

    org_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    slug = db.Column(db.String(64), unique=True, nullable=False)  # URL segment, e.g. "svdgc"
    name = db.Column(db.String(200), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    memberships = db.relationship('OrgMembership', backref='organization', lazy='dynamic')


class OrgMembership(db.Model):
    """A user's role within an org, optionally scoped to a single app.

    app='*' grants the role across all apps in the org.
    """
    __tablename__ = 'org_memberships'

    membership_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.org_id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    app = db.Column(
        db.Enum('dubs', 'tags', 'putt', '*', name='org_app_enum'),
        nullable=False, default='*',
    )
    role = db.Column(
        db.Enum('admin', 'director', 'viewer', name='org_role_enum'),
        nullable=False, default='viewer',
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('org_id', 'user_id', 'app', name='uq_org_user_app'),
    )


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    salt = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default='director')
    is_superuser = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True)

    sessions = db.relationship('UserSession', backref='user', lazy='dynamic')
    pii_access_logs = db.relationship('PiiAccessLog', backref='user', lazy='dynamic')
    memberships = db.relationship('OrgMembership', backref='user', lazy='dynamic')


class UserSession(db.Model):
    __tablename__ = 'user_sessions'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    session_token = db.Column(db.String(255), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    ip_address = db.Column(db.String(50), nullable=True)
    is_active = db.Column(db.Boolean, default=True)


class PiiAccessLog(db.Model):
    """Audit trail for access to member PII (contact info)."""
    __tablename__ = 'pii_access_log'

    log_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    member_id = db.Column(db.Integer, nullable=False)
    action = db.Column(db.Enum('view', 'create', 'update', 'delete'), nullable=False)
    accessed_at = db.Column(db.DateTime, default=datetime.utcnow)


class TenantMixin:
    """Mixin for org-scoped (tenant-owned) models.

    Declares the org_id FK once. The scoping layer (backend/shared/scoping.py)
    stamps org_id on insert and filters reads by the current org, so services
    generally do not set org_id manually.
    """

    @declared_attr
    def org_id(cls):  # noqa: N805
        return db.Column(
            db.Integer,
            db.ForeignKey('organizations.org_id'),
            nullable=False,
            index=True,
        )
