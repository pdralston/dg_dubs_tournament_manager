"""DG-Putt ace-pot read endpoint."""

from flask import Blueprint, jsonify
from backend.models import db, PuttAcePot as AcePot  # noqa: F401

ace_pot_bp = Blueprint('putt_ace_pot', __name__, url_prefix='/api/putt')


@ace_pot_bp.route('/ace-pot', methods=['GET'])
def get_ace_pot_entries():
    entries = AcePot.query.order_by(AcePot.date.asc(), AcePot.ace_pot_id.asc()).all()
    return jsonify([{
        'ace_pot_id': entry.ace_pot_id,
        'tournament_id': entry.tournament_id,
        'date': entry.date.isoformat(),
        'description': entry.description,
        'amount': float(entry.amount)
    } for entry in entries])
