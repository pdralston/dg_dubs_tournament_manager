"""API endpoints for authentication."""

from flask import Blueprint, jsonify, request, session, current_app
from backend.models import db, User, UserSession
from backend.shared.auth import (
    login_required, admin_required,
    resolve_org_role, resolve_membership_role, subscribed_apps,
)
from backend.shared.org_context import current_org_id

auth_api_bp = Blueprint('auth_api', __name__)


def _viewer_identity():
    """Anonymous/unauthenticated identity — consistent three-tier shape with
    everything empty so the client always receives the same keys."""
    return {
        'user_id': 0,
        'username': 'Viewer',
        'role': 'Viewer',          # legacy flat field (back-compat)
        'is_superuser': False,     # Site tier
        'org_role': None,          # Org tier: 'owner' | 'manager' | None
        'app_roles': {},           # App tier: {app: 'admin'|'director'|None}
    }


def _identity_payload(user):
    """Build the Site -> Org -> App identity for an authenticated user in the
    current org, using the same resolvers the backend uses to *enforce* access
    (so UI gating matches API behavior by construction)."""
    oid = current_org_id()
    return {
        'user_id': user.id,
        'username': user.username,
        'role': user.role,                         # legacy flat field (back-compat)
        'is_superuser': bool(user.is_superuser),   # Site tier
        'org_role': resolve_org_role(user.id),     # Org tier
        'app_roles': {                             # App tier (per subscribed app)
            app: resolve_membership_role(user.id, app)
            for app in subscribed_apps(oid)
        },
    }


@auth_api_bp.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({'error': 'Username and password required'}), 400

    auth = current_app.auth_manager
    ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
    success, result = auth.authenticate_user(data['username'], data['password'], ip)

    if success:
        session['session_token'] = result['session_token']
        session['user_id'] = result['user_id']
        session['username'] = result['username']
        session['role'] = result['role']
        return jsonify({
            'user_id': result['user_id'],
            'username': result['username'],
            'role': result['role'],
        })
    return jsonify({'error': result}), 401


@auth_api_bp.route('/api/auth/logout', methods=['POST'])
def logout():
    auth = current_app.auth_manager
    if 'session_token' in session:
        auth.logout_user(session['session_token'])
    session.clear()
    return jsonify({'message': 'Logged out'})


@auth_api_bp.route('/api/auth/me', methods=['GET'])
def me():
    """Return the current user's identity across the three authZ tiers
    (Site superuser -> Org governance role -> per-app role) for the current org.

    Response shape (always these keys, viewer = everything empty):
      user_id, username, role (legacy flat, back-compat),
      is_superuser (bool), org_role ('owner'|'manager'|None),
      app_roles ({app: 'admin'|'director'|None}).
    """
    if 'session_token' not in session:
        return jsonify(_viewer_identity())
    auth = current_app.auth_manager
    valid, info = auth.validate_session(session['session_token'])
    if not valid:
        session.clear()
        return jsonify(_viewer_identity())
    user = User.query.filter_by(id=info['user_id'], is_active=True).first()
    if not user:
        session.clear()
        return jsonify(_viewer_identity())
    return jsonify(_identity_payload(user))


@auth_api_bp.route('/api/auth/users', methods=['GET'])
@admin_required
def list_users():
    users = User.query.all()
    return jsonify([{
        'user_id': u.id, 'username': u.username, 'role': u.role,
        'is_active': u.is_active,
        'created_at': u.created_at.isoformat() if u.created_at else None,
    } for u in users])


@auth_api_bp.route('/api/auth/users', methods=['POST'])
@admin_required
def create_user():
    data = request.get_json()
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'error': 'Username and password required'}), 400

    role = data.get('role', 'director')
    if role not in ('director', 'admin'):
        return jsonify({'error': 'Invalid role'}), 400

    auth = current_app.auth_manager
    success, message = auth.create_user(data['username'], data['password'], role)
    if success:
        return jsonify({'message': message}), 201
    return jsonify({'error': message}), 400


@auth_api_bp.route('/api/auth/users/<int:user_id>', methods=['PUT'])
@login_required
def update_user(user_id):
    if session.get('role') == 'director' and session.get('user_id') != user_id:
        return jsonify({'error': 'Directors can only edit their own profile'}), 403

    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    if 'username' in data:
        existing = User.query.filter(User.username == data['username'], User.id != user_id).first()
        if existing:
            return jsonify({'error': 'Username already exists'}), 400
        user.username = data['username']

    if 'password' in data and data['password']:
        auth = current_app.auth_manager
        pw_hash, salt = auth.hash_password(data['password'])
        user.password_hash = pw_hash
        user.salt = salt

    if 'role' in data and session.get('role') == 'admin':
        if data['role'] in ('director', 'admin'):
            user.role = data['role']

    db.session.commit()
    return jsonify({'user_id': user.id, 'username': user.username, 'role': user.role})


@auth_api_bp.route('/api/auth/users/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    if session.get('user_id') == user_id:
        return jsonify({'error': 'Cannot delete your own account'}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    UserSession.query.filter_by(user_id=user_id).delete()
    db.session.delete(user)
    db.session.commit()
    return jsonify({'message': f'User {user.username} deleted'})
