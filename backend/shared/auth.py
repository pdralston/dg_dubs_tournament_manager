"""
Shared authentication & authorization module.

Provides:
  * AuthManager — password hashing, sessions.
  * Org/app-aware authorization: resolve a user's role within the current org
    for a given app, and the ``require_role`` decorator.
  * Back-compat ``login_required`` / ``admin_required`` decorators, now routed
    through the org-scoped membership check.

Shared across all apps (DG-Dubs, DG-Tags, DG-Putt).
"""

import hashlib
import secrets
from datetime import datetime, timedelta
from functools import wraps

from flask import session, jsonify
from backend.models import db, User, UserSession, OrgMembership
from backend.shared.org_context import current_org_id

# Role ranking for "at least this role" comparisons.
_ROLE_RANK = {'viewer': 0, 'director': 1, 'admin': 2}


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


def resolve_membership_role(user_id: int, app: str):
    """Return the effective role (str) for ``user_id`` in the current org for
    ``app``, or None if the user has no qualifying membership.

    Superusers implicitly get 'admin' in any org/app. An app-specific
    membership takes precedence over a wildcard ('*') membership; the higher
    role wins if both exist.
    """
    user = User.query.filter_by(id=user_id, is_active=True).first()
    if not user:
        return None
    if user.is_superuser:
        return 'admin'

    oid = current_org_id()
    memberships = OrgMembership.query.filter(
        OrgMembership.user_id == user_id,
        OrgMembership.org_id == oid,
        OrgMembership.app.in_((app, '*')),
    ).all()
    if not memberships:
        return None
    # Highest-ranked role among matching memberships.
    return max((m.role for m in memberships), key=lambda r: _ROLE_RANK.get(r, -1))


def require_role(app: str, role: str = 'viewer'):
    """Decorator: require the caller to hold at least ``role`` in the current
    org for ``app``.

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


def login_required(f):
    """Back-compat: requires an authenticated admin or director in the current
    org (any app, via wildcard membership).
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        info, err = _validate_session_or_fail()
        if err:
            return err
        effective = resolve_membership_role(info['user_id'], '*')
        if effective not in ('admin', 'director'):
            return jsonify({'error': 'Insufficient permissions'}), 403
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    """Back-compat: requires an admin in the current org."""
    @wraps(f)
    def decorated(*args, **kwargs):
        info, err = _validate_session_or_fail()
        if err:
            return err
        effective = resolve_membership_role(info['user_id'], '*')
        if effective != 'admin':
            return jsonify({'error': 'Admin required'}), 403
        return f(*args, **kwargs)
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
