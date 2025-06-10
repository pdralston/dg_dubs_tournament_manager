"""
API endpoints for storage management.
"""

from flask import Blueprint, jsonify, request
import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from tournament_core import TournamentRatingSystem

# Initialize blueprint
storage_bp = Blueprint('storage_api', __name__)

# Initialize rating system
rating_system = TournamentRatingSystem()

@storage_bp.route('/api/storage', methods=['GET'])
def get_storage_mode():
    """Get current storage mode."""
    return jsonify({
        'mode': 'database' if rating_system.use_db else 'json',
        'file': rating_system.data_file
    })

@storage_bp.route('/api/storage', methods=['PUT'])
def update_storage_mode():
    """Update storage mode."""
    data = request.get_json()
    
    if not data or 'mode' not in data:
        return jsonify({'error': 'Storage mode is required'}), 400
    
    mode = data['mode'].lower()
    
    if mode == 'database' or mode == 'db':
        rating_system.switch_storage_mode(True)
        return jsonify({
            'mode': 'database',
            'file': rating_system.data_file,
            'message': 'Switched to database storage'
        })
    elif mode == 'json':
        rating_system.switch_storage_mode(False)
        return jsonify({
            'mode': 'json',
            'file': rating_system.data_file,
            'message': 'Switched to JSON storage'
        })
    else:
        return jsonify({'error': 'Invalid storage mode. Use "database" or "json"'}), 400
