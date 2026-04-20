"""API endpoints for authentication."""

from flask import Blueprint, jsonify, request, session, current_app
from tournament_core.models import User

auth_api_bp = Blueprint('auth_api', __name__)


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
    if 'session_token' not in session:
        return jsonify({'user_id': 0, 'username': 'Viewer', 'role': 'Viewer'})
    auth = current_app.auth_manager
    valid, info = auth.validate_session(session['session_token'])
    if valid:
        return jsonify(info)
    session.clear()
    return jsonify({'user_id': 0, 'username': 'Viewer', 'role': 'Viewer'})


@auth_api_bp.route('/api/auth/users', methods=['GET'])
def list_users():
    if session.get('role') != 'admin':
        return jsonify({'error': 'Admin required'}), 403
    users = User.query.all()
    return jsonify([{
        'user_id': u.id, 'username': u.username, 'role': u.role,
        'is_active': u.is_active,
        'created_at': u.created_at.isoformat() if u.created_at else None,
    } for u in users])


@auth_api_bp.route('/api/auth/users', methods=['POST'])
def create_user():
    if session.get('role') != 'admin':
        return jsonify({'error': 'Admin required'}), 403
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
def update_user(user_id):
    from tournament_core.models import User, db

    # Directors can only edit themselves
    if session.get('role') == 'director' and session.get('user_id') != user_id:
        return jsonify({'error': 'Directors can only edit their own profile'}), 403
    if session.get('role') not in ('admin', 'director'):
        return jsonify({'error': 'Authentication required'}), 401

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

    # Only admins can change roles
    if 'role' in data and session.get('role') == 'admin':
        if data['role'] in ('director', 'admin'):
            user.role = data['role']

    db.session.commit()
    return jsonify({'user_id': user.id, 'username': user.username, 'role': user.role})
