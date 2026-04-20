"""
API endpoints for storage management.
Storage is now always MySQL — this endpoint reports the current mode.
"""

from flask import Blueprint, jsonify

storage_bp = Blueprint('storage_api', __name__)


@storage_bp.route('/api/storage', methods=['GET'])
def get_storage_mode():
    return jsonify({'mode': 'mysql', 'message': 'Using MySQL via SQLAlchemy'})
