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
    org_roles = db.relationship('OrgRole', backref='organization', lazy='dynamic')


class OrgRole(db.Model):
    """Governance-tier role: org-wide, cross-app (§13).

    This is a *distinct axis* from the per-app ``OrgMembership`` ladder — not a
    higher rung on it. Owners/managers manage other org users and derive
    app-admin on every subscribed app (see ``resolve_membership_role``); they
    hold no ``app`` column because their power is org-wide.

      * owner   — manage owners+managers, provision app users, (future) billing.
      * manager — manage other managers, provision app users; no billing.

    At most one governance role per user per org (UNIQUE(org_id, user_id)).
    This is a governance table: it references an org but is not org-stamped by
    the tenant flush hook; it is written only by the seed/migration and (future)
    governance endpoints.
    """
    __tablename__ = 'org_roles'

    org_role_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.org_id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    role = db.Column(
        db.Enum('owner', 'manager', name='org_governance_role_enum'),
        nullable=False,
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('org_id', 'user_id', name='uq_org_user_role'),
    )


class OrgMembership(db.Model):
    """A user's role within an org, scoped to a single app (§13).

    One row per ``(user, app)``. A multi-app user holds multiple rows — one per
    app — each with its own role; there is no wildcard. Per-row storage is what
    makes "no cross-app visibility" fall out for free and preserves the
    per-app authz check and the ``(org_id, user_id, app)`` unique constraint.

      * admin    — full CRUD within that one app (incl. PII/inventory) and may
        grant/revoke admin & director memberships for that app only.
      * director — event/data operations within one app; PII write-blind (Tags).

    ``viewer`` is not a grantable role: "viewer" means *no membership* (anyone,
    including unauthenticated users). The ``'*'`` wildcard is likewise gone —
    its sole prior use ("org admin") is now the ``OrgRole`` governance tier.
    """
    __tablename__ = 'org_memberships'

    membership_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    org_id = db.Column(db.Integer, db.ForeignKey('organizations.org_id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    app = db.Column(
        db.Enum('dubs', 'tags', 'putt', name='org_app_enum'),
        nullable=False,
    )
    role = db.Column(
        db.Enum('admin', 'director', name='org_role_enum'),
        nullable=False,
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
