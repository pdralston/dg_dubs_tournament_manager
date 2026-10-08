"""
Shared authentication & authorization module.

Provides:
  * AuthManager — password hashing, sessions.
  * Two-axis authorization (§13):
      - App axis: ``resolve_membership_role`` + ``require_role`` gate access
        within a single app (admin/director; absence = viewer).
      - Governance axis: ``resolve_org_role`` + ``require_org_role`` gate
        org-wide owner/manager powers. A governance role derives app-admin on
        every subscribed app.
  * Back-compat ``login_required`` / ``admin_required`` decorators, routed
    through the governance + membership checks (no wildcard).

Shared across all apps (DG-Dubs, DG-Tags, DG-Putt).
"""

import hashlib
import secrets
from datetime import datetime, timedelta
from functools import wraps

from flask import session, jsonify
from backend.models import db, User, UserSession, OrgMembership, OrgRole
from backend.shared.org_context import current_org_id

# App-axis role ranking for "at least this role" comparisons (§13).
# 'viewer' is no longer a grantable role — absence of a membership *is* viewer.
_ROLE_RANK = {'director': 0, 'admin': 1}

# Governance-axis ranking (owner outranks manager).
_ORG_ROLE_RANK = {'manager': 0, 'owner': 1}


def subscribed_apps(org_id: int):
    """Apps an org is entitled to use.

    Stub for the deferred entitlements work (§13.8 / future
    ``org_app_subscriptions``): returns all apps for every org for now. This is
    the single seam the derived-admin rule reads, so nothing else changes when
    real subscriptions land.
    """
    return ('dubs', 'tags', 'putt')


def _validate_session_or_fail():
    """Validate session token against DB. Returns (info, error_response)."""
    from flask import current_app
    token = session.get('session_token')
    if not token:
        return None, (jsonify({'error': 'Authentication required'}), 401)
    valid, info = current_app.auth_manager.validate_session(token)
    if not valid:
        session.clear()
        return None, (jsonify({'error': 'Authentication required'}), 401)
    return info, None


def resolve_org_role(user_id: int):
    """Return the governance role ('owner'/'manager') for ``user_id`` in the
    current org, or None. Superusers are not special-cased here (they are
    handled at the app-role layer)."""
    oid = current_org_id()
    row = OrgRole.query.filter_by(org_id=oid, user_id=user_id).first()
    return row.role if row else None


def resolve_membership_role(user_id: int, app: str):
    """Return the effective app-axis role (str) for ``user_id`` in the current
    org for ``app``, or None if the user has no qualifying access.

    Resolution order (§13.5):
      1. Superuser → 'admin' (platform bypass, unchanged).
      2. A governance role (owner/manager) in the current org derives 'admin'
         on every *subscribed* app — no per-app membership row required.
      3. Otherwise the explicit ``org_memberships`` row for that app
         (admin/director), or None.
    """
    user = User.query.filter_by(id=user_id, is_active=True).first()
    if not user:
        return None
    if user.is_superuser:
        return 'admin'

    oid = current_org_id()

    # (2) Derived app-admin for governance-tier users on subscribed apps.
    if resolve_org_role(user_id) is not None and app in subscribed_apps(oid):
        return 'admin'

    # (3) Explicit per-app membership.
    m = OrgMembership.query.filter_by(
        org_id=oid, user_id=user_id, app=app,
    ).first()
    return m.role if m else None


def require_role(app: str, role: str = 'director'):
    """Decorator: require the caller to hold at least ``role`` in the current
    org for ``app``. There is no viewer gate anymore — public endpoints drop
    the decorator entirely.

    Usage:
        @require_role(app='tags', role='director')
        @require_role(app='dubs', role='admin')
    """
    needed = _ROLE_RANK.get(role, 0)

    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            info, err = _validate_session_or_fail()
            if err:
                return err
            effective = resolve_membership_role(info['user_id'], app)
            if effective is None or _ROLE_RANK.get(effective, -1) < needed:
                return jsonify({'error': 'Insufficient permissions'}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator


def require_org_role(role: str = 'manager'):
    """Decorator: require the caller to hold at least the governance role
    ``role`` (owner > manager) in the current org. Superusers bypass.

    Scaffolding for future ``/api/org/*`` governance endpoints (§13.8); not yet
    attached to any route.
    """
    needed = _ORG_ROLE_RANK.get(role, 0)

    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            info, err = _validate_session_or_fail()
            if err:
                return err
            user = User.query.filter_by(id=info['user_id'], is_active=True).first()
            if user and user.is_superuser:
                return f(*args, **kwargs)
            effective = resolve_org_role(info['user_id'])
            if effective is None or _ORG_ROLE_RANK.get(effective, -1) < needed:
                return jsonify({'error': 'Insufficient permissions'}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator


def login_required(f):
    """Back-compat: requires an authenticated user with *some* access in the
    current org — a governance role or any app membership (§13.5).
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        info, err = _validate_session_or_fail()
        if err:
            return err
        uid = info['user_id']
        user = User.query.filter_by(id=uid, is_active=True).first()
        has_access = bool(
            (user and user.is_superuser)
            or resolve_org_role(uid) is not None
            or OrgMembership.query.filter_by(
                org_id=current_org_id(), user_id=uid,
            ).first() is not None
        )
        if not has_access:
            return jsonify({'error': 'Insufficient permissions'}), 403
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    """Back-compat: requires an org-admin equivalent in the current org — a
    superuser or any governance-tier (owner/manager) holder (§13.5).
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        info, err = _validate_session_or_fail()
        if err:
            return err
        uid = info['user_id']
        user = User.query.filter_by(id=uid, is_active=True).first()
        if (user and user.is_superuser) or resolve_org_role(uid) is not None:
            return f(*args, **kwargs)
        return jsonify({'error': 'Admin required'}), 403
    return decorated


class AuthManager:
    """Manages authentication and user sessions."""

    def hash_password(self, password, salt=None):
        if salt is None:
            salt = secrets.token_hex(32)
        password_hash = hashlib.pbkdf2_hmac(
            'sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000
        )
        return password_hash.hex(), salt

    def verify_password(self, password, stored_hash, salt):
        password_hash, _ = self.hash_password(password, salt)
        return secrets.compare_digest(password_hash, stored_hash)

    def create_user(self, username, password, role='director'):
        existing = User.query.filter_by(username=username).first()
        if existing:
            return False, "Username already exists"
        password_hash, salt = self.hash_password(password)
        user = User(username=username, password_hash=password_hash, salt=salt, role=role)
        db.session.add(user)
        db.session.commit()
        return True, "User created successfully"

    def authenticate_user(self, username, password, ip_address=None):
        user = User.query.filter_by(username=username, is_active=True).first()
        if not user:
            return False, "Invalid username or password"
        if not self.verify_password(password, user.password_hash, user.salt):
            return False, "Invalid username or password"

        session_token = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(hours=24)

        us = UserSession(
            user_id=user.id, session_token=session_token,
            expires_at=expires_at, ip_address=ip_address,
        )
        db.session.add(us)
        user.last_login = datetime.now()
        db.session.commit()

        return True, {
            'user_id': user.id, 'username': user.username,
            'role': user.role, 'session_token': session_token,
        }

    def validate_session(self, session_token):
        us = UserSession.query.filter_by(session_token=session_token, is_active=True).first()
        if not us:
            return False, None
        user = User.query.filter_by(id=us.user_id, is_active=True).first()
        if not user:
            return False, None
        if datetime.now() > us.expires_at:
            us.is_active = False
            db.session.commit()
            return False, None
        return True, {'user_id': user.id, 'username': user.username, 'role': user.role}

    def logout_user(self, session_token):
        us = UserSession.query.filter_by(session_token=session_token).first()
        if us:
            us.is_active = False
            db.session.commit()
        return True
