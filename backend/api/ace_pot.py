"""API endpoints for ace pot management."""

from flask import Blueprint, jsonify, request, current_app

ace_pot_bp = Blueprint('ace_pot_api', __name__)


def _apm():
    return current_app.rating_system.ace_pot_manager


@ace_pot_bp.route('/api/ace-pot/balance', methods=['GET'])
def get_balance():
    return jsonify(_apm().get_balance())


@ace_pot_bp.route('/api/ace-pot/config', methods=['GET'])
def get_config():
    return jsonify(_apm().get_config())


@ace_pot_bp.route('/api/ace-pot/config', methods=['PUT'])
def update_config():
    data = request.get_json()
    if not data or 'cap_amount' not in data:
        return jsonify({'error': 'cap_amount required'}), 400
    _apm().update_config(float(data['cap_amount']))
    return jsonify(_apm().get_config())


@ace_pot_bp.route('/api/ace-pot/ledger', methods=['GET'])
def get_ledger():
    return jsonify(_apm().get_ledger())


@ace_pot_bp.route('/api/ace-pot/balance', methods=['PUT'])
def set_balance():
    data = request.get_json()
    if not data or 'amount' not in data:
        return jsonify({'error': 'amount required'}), 400
    _apm().set_balance(float(data['amount']), data.get('description'))
    return jsonify(_apm().get_balance())


@ace_pot_bp.route('/api/ace-pot/tournament', methods=['POST'])
def process_tournament_ace_pot():
    """Process ace pot buy-ins and optional payout for a tournament."""
    data = request.get_json()
    if not data or 'tournament_id' not in data:
        return jsonify({'error': 'tournament_id required'}), 400

    tid = data['tournament_id']
    result = {}

    buy_ins = data.get('buy_in_players', [])
    if buy_ins:
        result['buy_ins'] = _apm().process_batch_buy_ins(tid, buy_ins)

    recipients = data.get('payout_recipients', [])
    if recipients:
        from tournament_core.models import Player, Tournament, db
        pre_balance = _apm().get_balance()
        total_payout = pre_balance.get('current', pre_balance.get('total', 0))
        per_person = total_payout / len(recipients) if total_payout > 0 else 0

        # Create a single ledger entry for the full payout listing all recipients
        names = ', '.join(recipients)
        _apm().add_entry(
            description=f"Ace pot payout to {names}",
            amount=-total_payout,
            tournament_id=tid,
        )

        # Credit each recipient's seasonal_cash
        for name in recipients:
            p = Player.query.filter_by(name=name).first()
            if p:
                p.seasonal_cash = float(p.seasonal_cash) + per_person

        # Store all recipient names on the tournament
        t = Tournament.query.get(tid)
        if t:
            t.ace_pot_paid = True
            t.ace_pot_paid_to = names
        db.session.commit()
    result['payouts'] = len(recipients)

    result['balance'] = _apm().get_balance()
    return jsonify(result)
