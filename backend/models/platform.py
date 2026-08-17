"""Platform-level models shared across all apps.

Includes authentication (User, UserSession) and audit logging (PiiAccessLog).
"""

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    salt = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default='director')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.Boolean, default=True)

    sessions = db.relationship('UserSession', backref='user', lazy='dynamic')
    pii_access_logs = db.relationship('PiiAccessLog', backref='user', lazy='dynamic')


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
