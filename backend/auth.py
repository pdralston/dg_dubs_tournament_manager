#!/usr/bin/env python3
"""
Authentication module for the Disc Golf League Tournament Rating System.
Uses SQLAlchemy models backed by MySQL.
"""

import hashlib
import secrets
from datetime import datetime, timedelta
from functools import wraps

from flask import session, jsonify
from tournament_core.models import db, User, UserSession


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


def login_required(f):
    """Decorator that requires an authenticated admin or director."""
    @wraps(f)
    def decorated(*args, **kwargs):
        info, err = _validate_session_or_fail()
        if err:
            return err
        if info.get('role') not in ('admin', 'director'):
            return jsonify({'error': 'Insufficient permissions'}), 403
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    """Decorator that requires an admin user."""
    @wraps(f)
    def decorated(*args, **kwargs):
        info, err = _validate_session_or_fail()
        if err:
            return err
        if info.get('role') != 'admin':
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
