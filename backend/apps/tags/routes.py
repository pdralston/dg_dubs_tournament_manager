"""
DG-Tags API Routes

Endpoints for bag tag event management, member management, inventory,
and standings. Implements the full event lifecycle:
Pending → Scheduled → In Progress → Complete
"""

from datetime import datetime
from flask import Blueprint, jsonify, request, session
from backend.models import (
    db, TagMember, MemberContactInfo, TagEvent, TagRegistration,
    TagHistory, TagInventory, TagUnavailable, PiiAccessLog,
)
from backend.shared.auth import login_required, admin_required
from . import services

tags_bp = Blueprint('tags_api', __name__, url_prefix='/api/tags')


# ═══════════════════════════════════════════════════════════════════════════════
# Members
# ═══════════════════════════════════════════════════════════════════════════════

@tags_bp.route('/members', methods=['GET'])
def get_members():
    """List all active members. PII is excluded for non-admin users."""
    members = TagMember.query.filter_by(is_active=True).order_by(TagMember.name).all()
    role = session.get('role', 'Viewer')

    result = []
    for m in members:
        entry = {
            'member_id': m.member_id,
            'name': m.name,
            'udisc_name': m.udisc_name,
            'current_tag': m.current_tag,
            'is_active': m.is_active,
        }
        # Admin-only: include PII
        if role == 'admin' and m.contact_info:
            entry['email'] = m.contact_info.email
            entry['phone'] = m.contact_info.phone
            entry['shipping_address'] = m.contact_info.shipping_address
            entry['payment_method'] = m.contact_info.payment_method
            _log_pii_access(m.member_id, 'view')
        result.append(entry)

    return jsonify(result)


@tags_bp.route('/members/search', methods=['GET'])
def search_members():
    """
    Search members by name or UDisc name.
    Used for Monthly same-day registration to find existing members.
    Query param: ?q=search_term
    """
    query = request.args.get('q', '').strip()
    if not query or len(query) < 2:
        return jsonify({'error': 'Search query must be at least 2 characters'}), 400

    results = services.search_members(query)
    return jsonify(results)


@tags_bp.route('/members/check-duplicate', methods=['POST'])
@login_required
def check_duplicate():
    """
    Check for potential duplicate members before creating a new one.
    Returns list of potential matches for TD/Admin to confirm.
    """
    data = request.get_json()
    if not data or not data.get('name'):
        return jsonify({'error': 'Name is required'}), 400

    candidates = services.check_duplicate_member(
        name=data['name'],
        udisc_name=data.get('udisc_name')
    )

    return jsonify({
        'is_duplicate': len(candidates) > 0,
        'candidates': candidates,
    })


@tags_bp.route('/members', methods=['POST'])
@login_required
def create_member():
    """
    Create a new member. Directors can submit PII but cannot read it back.
    Optionally assign a tag via 'current_tag' field.
    """
    data = request.get_json()
    if not data or not data.get('name'):
        return jsonify({'error': 'Name is required'}), 400

    member = TagMember(
        name=data['name'],
        udisc_name=data.get('udisc_name'),
        current_tag=data.get('current_tag'),
    )
    db.session.add(member)
    db.session.flush()  # get member_id

    # Store PII in separate table
    email = data.get('email')
    phone = data.get('phone')
    shipping_address = data.get('shipping_address')
    payment_method = data.get('payment_method')

    if email or phone or shipping_address or payment_method:
        contact = MemberContactInfo(
            member_id=member.member_id,
            email=email,
            phone=phone,
            shipping_address=shipping_address,
            payment_method=payment_method,
        )
        db.session.add(contact)
        _log_pii_access(member.member_id, 'create')

    db.session.commit()

    return jsonify({
        'member_id': member.member_id,
        'name': member.name,
        'udisc_name': member.udisc_name,
        'current_tag': member.current_tag,
    }), 201


@tags_bp.route('/members/<int:member_id>', methods=['PUT'])
@login_required
def update_member(member_id):
    """Update a member. PII fields only writable by admin."""
    member = TagMember.query.get(member_id)
    if not member:
        return jsonify({'error': 'Member not found'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    if 'name' in data:
        member.name = data['name']
    if 'udisc_name' in data:
        member.udisc_name = data['udisc_name']
    if 'current_tag' in data:
        member.current_tag = data['current_tag']
    if 'is_active' in data:
        member.is_active = data['is_active']

    # PII updates — admin only
    role = session.get('role', 'Viewer')
    if role == 'admin':
        contact = MemberContactInfo.query.get(member_id)
        if not contact:
            contact = MemberContactInfo(member_id=member_id)
            db.session.add(contact)
        if 'email' in data:
            contact.email = data['email']
        if 'phone' in data:
            contact.phone = data['phone']
        if 'shipping_address' in data:
            contact.shipping_address = data['shipping_address']
        if 'payment_method' in data:
            contact.payment_method = data['payment_method']
        _log_pii_access(member_id, 'update')

    db.session.commit()
    return jsonify({'member_id': member.member_id, 'name': member.name})


@tags_bp.route('/members/<int:member_id>', methods=['DELETE'])
@admin_required
def delete_member(member_id):
    """Soft-delete a member and hard-delete their PII."""
    member = TagMember.query.get(member_id)
    if not member:
        return jsonify({'error': 'Member not found'}), 404

    # Hard-delete PII
    contact = MemberContactInfo.query.get(member_id)
    if contact:
        db.session.delete(contact)
        _log_pii_access(member_id, 'delete')

    # Soft-delete member
    member.is_active = False
    member.current_tag = None
    db.session.commit()
    return jsonify({'message': f'Member {member.name} deactivated, PII purged'})


# ═══════════════════════════════════════════════════════════════════════════════
# Events
# ═══════════════════════════════════════════════════════════════════════════════

@tags_bp.route('/events', methods=['GET'])
def get_events():
    """
    List events. Unauthenticated users only see scheduled/in_progress/complete.
    Admins/TDs see all including pending.
    """
    role = session.get('role', 'Viewer')
    query = TagEvent.query.order_by(TagEvent.date.desc())

    if role not in ('admin', 'director'):
        query = query.filter(TagEvent.status != 'pending')

    events = query.all()
    return jsonify([
        {
            'event_id': e.event_id,
            'event_type': e.event_type,
            'date': e.date.isoformat(),
            'course': e.course,
            'status': e.status,
            'notes': e.notes,
            'participant_count': TagRegistration.query.filter_by(
                event_id=e.event_id
            ).count(),
        }
        for e in events
    ])


@tags_bp.route('/events', methods=['POST'])
@login_required
def create_event():
    """Create a new tag event. Starts in 'pending' status."""
    data = request.get_json()
    if not data or not data.get('date'):
        return jsonify({'error': 'Date is required'}), 400
    if not data.get('event_type') or data['event_type'] not in ('annual', 'monthly'):
        return jsonify({'error': "event_type must be 'annual' or 'monthly'"}), 400

    # Parse date string
    date_value = data['date']
    if isinstance(date_value, str):
        try:
            date_value = datetime.strptime(date_value, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

    event = TagEvent(
        event_type=data['event_type'],
        date=date_value,
        course=data.get('course'),
        notes=data.get('notes'),
    )
    db.session.add(event)
    db.session.commit()
    return jsonify({
        'event_id': event.event_id,
        'event_type': event.event_type,
        'status': event.status,
    }), 201


@tags_bp.route('/events/<int:event_id>', methods=['GET'])
def get_event(event_id):
    """Get event details including registrations."""
    event = TagEvent.query.get(event_id)
    if not event:
        return jsonify({'error': 'Event not found'}), 404

    # Check visibility
    role = session.get('role', 'Viewer')
    if event.status == 'pending' and role not in ('admin', 'director'):
        return jsonify({'error': 'Event not found'}), 404

    registrations = TagRegistration.query.filter_by(event_id=event_id).all()
    regs = []
    for r in registrations:
        member = TagMember.query.get(r.member_id)
        regs.append({
            'reg_id': r.reg_id,
            'member_id': r.member_id,
            'name': member.name if member else 'Unknown',
            'udisc_name': member.udisc_name if member else None,
            'is_player': r.is_player,
            'is_checked_in': r.is_checked_in,
            'is_dnf': r.is_dnf,
            'old_tag': r.old_tag,
            'round_score': r.round_score,
            'new_tag': r.new_tag,
            'position': r.position,
        })

    return jsonify({
        'event_id': event.event_id,
        'event_type': event.event_type,
        'date': event.date.isoformat(),
        'course': event.course,
        'status': event.status,
        'notes': event.notes,
        'registrations': regs,
    })


# ═══════════════════════════════════════════════════════════════════════════════
# Registration (Pre-Reg and Same-Day)
# ═══════════════════════════════════════════════════════════════════════════════

@tags_bp.route('/events/<int:event_id>/register', methods=['POST'])
@login_required
def register_player(event_id):
    """
    Register a player/non-player for an event.
    For same-day registration, set is_same_day=true to auto-check-in.
    For Monthly same-day, auto-assigns lowest available tag as old_tag.
    """
    event = TagEvent.query.get(event_id)
    if not event:
        return jsonify({'error': 'Event not found'}), 404
    if event.status not in ('pending', 'scheduled'):
        return jsonify({'error': 'Registration is closed for this event'}), 400

    data = request.get_json()
    if not data or not data.get('member_id'):
        return jsonify({'error': 'member_id is required'}), 400

    member_id = data['member_id']
    member = TagMember.query.get(member_id)
    if not member:
        return jsonify({'error': 'Member not found'}), 404

    # Check for existing registration
    existing = TagRegistration.query.filter_by(
        event_id=event_id, member_id=member_id
    ).first()
    if existing:
        return jsonify({'error': 'Member is already registered for this event'}), 409

    is_player = data.get('is_player', True)
    is_same_day = data.get('is_same_day', False)
    old_tag = data.get('old_tag')

    # For same-day monthly registration of a new member (no current tag)
    if is_same_day and event.event_type == 'monthly' and is_player and not old_tag:
        season_year = event.date.year
        new_tag_num = services.get_lowest_available_tag(season_year)
        if new_tag_num is None:
            return jsonify({'error': 'No tags available in inventory'}), 400
        old_tag = new_tag_num
        # Assign this tag to the member
        member.current_tag = new_tag_num

    # For pre-registration, old_tag comes from member's current tag if not specified
    if old_tag is None and member.current_tag is not None:
        old_tag = member.current_tag

    reg = TagRegistration(
        event_id=event_id,
        member_id=member_id,
        is_player=is_player,
        is_checked_in=is_same_day,  # Same-day = auto checked in
        old_tag=old_tag,
    )
    db.session.add(reg)
    db.session.commit()

    return jsonify({
        'reg_id': reg.reg_id,
        'member_id': member_id,
        'name': member.name,
        'is_player': reg.is_player,
        'is_checked_in': reg.is_checked_in,
        'old_tag': reg.old_tag,
    }), 201


@tags_bp.route('/events/<int:event_id>/register/import', methods=['POST'])
@login_required
def import_registrations(event_id):
    """
    Bulk import registrations from a DGScene CSV file.
    Creates members that don't exist and registers them for the event.
    Event must be in 'pending' status.
    """
    event = TagEvent.query.get(event_id)
    if not event:
        return jsonify({'error': 'Event not found'}), 404
    if event.status != 'pending':
        return jsonify({'error': 'Can only import registrations for pending events'}), 400

    file = request.files.get('file')
    if not file:
        return jsonify({'error': 'No file provided'}), 400

    try:
        content = file.read().decode('utf-8-sig')
    except UnicodeDecodeError:
        return jsonify({'error': 'File must be UTF-8 encoded CSV'}), 400

    parsed = services.parse_registration_csv(content)
    if not parsed:
        return jsonify({'error': 'No valid registrations found in file'}), 400

    # Determine player vs non-player division values
    # The caller can specify which division value means "non-player"
    non_player_divisions = request.form.getlist('non_player_divisions')
    non_player_divisions_lower = [d.lower() for d in non_player_divisions]

    created_members = []
    registered = []
    skipped = []

    for entry in parsed:
        name = entry['name']

        # Check if member already exists (by name match)
        existing_member = TagMember.query.filter(
            db.func.lower(TagMember.name) == name.lower()
        ).first()

        if existing_member:
            member = existing_member
        else:
            # Create new member
            member = TagMember(
                name=name,
                udisc_name=entry.get('udisc_name') or name,
            )
            db.session.add(member)
            db.session.flush()

            # Store PII
            if entry.get('email') or entry.get('phone') or entry.get('shipping_address'):
                contact = MemberContactInfo(
                    member_id=member.member_id,
                    email=entry.get('email'),
                    phone=entry.get('phone'),
                    shipping_address=entry.get('shipping_address'),
                )
                db.session.add(contact)
                _log_pii_access(member.member_id, 'create')

            created_members.append({
                'member_id': member.member_id,
                'name': member.name,
            })

        # Check if already registered for this event
        existing_reg = TagRegistration.query.filter_by(
            event_id=event_id, member_id=member.member_id
        ).first()
        if existing_reg:
            skipped.append({'name': name, 'reason': 'already registered'})
            continue

        # Determine player status from division
        is_player = True
        if non_player_divisions_lower:
            division = entry.get('division', '').lower()
            if division in non_player_divisions_lower:
                is_player = False

        reg = TagRegistration(
            event_id=event_id,
            member_id=member.member_id,
            is_player=is_player,
            old_tag=entry.get('previous_tag'),
        )
        db.session.add(reg)
        registered.append({
            'member_id': member.member_id,
            'name': name,
            'is_player': is_player,
            'old_tag': entry.get('previous_tag'),
        })

    db.session.commit()

    return jsonify({
        'created_members': len(created_members),
        'registered': len(registered),
        'skipped': len(skipped),
        'details': {
            'new_members': created_members,
            'registrations': registered,
            'skipped': skipped,
        }
    })


# ═══════════════════════════════════════════════════════════════════════════════
# Check-in
# ═══════════════════════════════════════════════════════════════════════════════

@tags_bp.route('/events/<int:event_id>/checkin', methods=['POST'])
@login_required
def check_in_player(event_id):
    """
    Check in a pre-registered player. Event must be in 'scheduled' status.
    Accepts {member_id} or {reg_id}. Optionally update old_tag.
    """
    event = TagEvent.query.get(event_id)
    if not event:
        return jsonify({'error': 'Event not found'}), 404
    if event.status != 'scheduled':
        return jsonify({'error': 'Check-in is only available for scheduled events'}), 400

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    # Find registration by member_id or reg_id
    reg = None
    if data.get('reg_id'):
        reg = TagRegistration.query.get(data['reg_id'])
        if reg and reg.event_id != event_id:
            reg = None
    elif data.get('member_id'):
        reg = TagRegistration.query.filter_by(
            event_id=event_id, member_id=data['member_id']
        ).first()

    if not reg:
        return jsonify({'error': 'Registration not found for this event'}), 404

    reg.is_checked_in = True

    # Allow updating old_tag at check-in time
    if 'old_tag' in data and data['old_tag'] is not None:
        reg.old_tag = data['old_tag']

    db.session.commit()

    member = TagMember.query.get(reg.member_id)
    return jsonify({
        'reg_id': reg.reg_id,
        'member_id': reg.member_id,
        'name': member.name if member else 'Unknown',
        'is_checked_in': True,
        'old_tag': reg.old_tag,
    })


@tags_bp.route('/events/<int:event_id>/registrations/<int:reg_id>', methods=['PUT'])
@login_required
def update_registration(event_id, reg_id):
    """
    Update a registration. Allows modifying is_player, old_tag, is_dnf.
    Available during 'scheduled' or 'in_progress' status.
    """
    event = TagEvent.query.get(event_id)
    if not event:
        return jsonify({'error': 'Event not found'}), 404
    if event.status not in ('scheduled', 'in_progress'):
        return jsonify({'error': 'Cannot modify registrations in this state'}), 400

    reg = TagRegistration.query.get(reg_id)
    if not reg or reg.event_id != event_id:
        return jsonify({'error': 'Registration not found'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    if 'is_player' in data:
        reg.is_player = data['is_player']
    if 'old_tag' in data:
        reg.old_tag = data['old_tag']
    if 'is_dnf' in data:
        reg.is_dnf = data['is_dnf']
    if 'is_checked_in' in data:
        reg.is_checked_in = data['is_checked_in']

    db.session.commit()

    member = TagMember.query.get(reg.member_id)
    return jsonify({
        'reg_id': reg.reg_id,
        'member_id': reg.member_id,
        'name': member.name if member else 'Unknown',
        'is_player': reg.is_player,
        'is_checked_in': reg.is_checked_in,
        'is_dnf': reg.is_dnf,
        'old_tag': reg.old_tag,
    })


# ═══════════════════════════════════════════════════════════════════════════════
# State Transitions
# ═══════════════════════════════════════════════════════════════════════════════

@tags_bp.route('/events/<int:event_id>/transition', methods=['POST'])
@login_required
def transition_event(event_id):
    """
    Advance event to next status. Accepts {target_status, season_year}.
    Triggers appropriate workflow for the transition.
    """
    data = request.get_json()
    if not data or not data.get('target_status'):
        return jsonify({'error': 'target_status is required'}), 400

    target = data['target_status']
    season_year = data.get('season_year', datetime.now().year)

    event = TagEvent.query.get(event_id)
    if not event:
        return jsonify({'error': 'Event not found'}), 404

    if not event.can_transition_to(target):
        return jsonify({
            'error': f"Cannot transition from '{event.status}' to '{target}'."
        }), 400

    if target == 'scheduled':
        success, msg = services.transition_to_scheduled(event_id)
        if not success:
            return jsonify({'error': msg}), 400
        return jsonify({'message': msg, 'status': 'scheduled'})

    elif target == 'in_progress':
        success, msg, details = services.transition_to_in_progress(event_id, season_year)
        if not success:
            return jsonify({'error': msg}), 400
        return jsonify({'message': msg, 'status': 'in_progress', 'details': details})

    elif target == 'complete':
        success, msg, results = services.transition_to_complete(event_id, season_year)
        if not success:
            return jsonify({'error': msg}), 400
        return jsonify({'message': msg, 'status': 'complete', 'results': results})

    return jsonify({'error': f"Unknown target status: {target}"}), 400


# ═══════════════════════════════════════════════════════════════════════════════
# Results / Scores
# ═══════════════════════════════════════════════════════════════════════════════

@tags_bp.route('/events/<int:event_id>/scores', methods=['POST'])
@login_required
def submit_scores(event_id):
    """
    Submit scores for an event (manual entry).
    Accepts {scores: [{member_id, round_score}, ...]}.
    Event must be 'in_progress'.
    """
    event = TagEvent.query.get(event_id)
    if not event:
        return jsonify({'error': 'Event not found'}), 404
    if event.status != 'in_progress':
        return jsonify({'error': 'Scores can only be submitted for in-progress events'}), 400

    data = request.get_json()
    scores = data.get('scores', []) if data else []
    if not scores:
        return jsonify({'error': 'No scores provided'}), 400

    updated = 0
    for entry in scores:
        mid = entry.get('member_id')
        score = entry.get('round_score')
        if mid is None or score is None:
            continue
        reg = TagRegistration.query.filter_by(event_id=event_id, member_id=mid).first()
        if reg and reg.is_player and reg.is_checked_in:
            reg.round_score = int(score)
            updated += 1

    db.session.commit()
    return jsonify({'message': f'Updated {updated} scores'})


@tags_bp.route('/events/<int:event_id>/scores/import', methods=['POST'])
@login_required
def import_scores(event_id):
    """
    Import scores from a UDisc CSV or XLSX file.
    Attempts to match players by UDisc name.
    Returns matched and unmatched players for resolution.
    Event must be 'in_progress'.
    """
    event = TagEvent.query.get(event_id)
    if not event:
        return jsonify({'error': 'Event not found'}), 404
    if event.status != 'in_progress':
        return jsonify({'error': 'Scores can only be imported for in-progress events'}), 400

    file = request.files.get('file')
    if not file:
        return jsonify({'error': 'No file provided'}), 400

    filename = file.filename or 'results.csv'
    content = file.read()

    try:
        results_data = services.parse_results_file(content, filename)
    except ImportError as e:
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        return jsonify({'error': f'Failed to parse file: {str(e)}'}), 400

    if not results_data:
        return jsonify({'error': 'No valid results found in file'}), 400

    # Match results to registered players
    matched, unmatched = services.match_udisc_results(results_data, event_id)

    # Auto-apply matched scores
    applied = 0
    for m in matched:
        reg = TagRegistration.query.get(m['reg_id'])
        if reg:
            reg.round_score = m['round_score']
            applied += 1

    db.session.commit()

    return jsonify({
        'applied': applied,
        'matched': matched,
        'unmatched': unmatched,
        'needs_resolution': len(unmatched) > 0,
    })


@tags_bp.route('/events/<int:event_id>/scores/resolve', methods=['POST'])
@login_required
def resolve_scores(event_id):
    """
    Manually resolve unmatched score imports.
    Accepts {resolutions: [{reg_id, round_score}, ...]}.
    """
    event = TagEvent.query.get(event_id)
    if not event:
        return jsonify({'error': 'Event not found'}), 404
    if event.status != 'in_progress':
        return jsonify({'error': 'Can only resolve scores for in-progress events'}), 400

    data = request.get_json()
    resolutions = data.get('resolutions', []) if data else []
    if not resolutions:
        return jsonify({'error': 'No resolutions provided'}), 400

    resolved = 0
    for entry in resolutions:
        reg_id = entry.get('reg_id')
        score = entry.get('round_score')
        if reg_id is None or score is None:
            continue
        reg = TagRegistration.query.get(reg_id)
        if reg and reg.event_id == event_id:
            reg.round_score = int(score)
            resolved += 1

    db.session.commit()
    return jsonify({'message': f'Resolved {resolved} scores'})


# ═══════════════════════════════════════════════════════════════════════════════
# Inventory Management
# ═══════════════════════════════════════════════════════════════════════════════

@tags_bp.route('/inventory', methods=['GET'])
@login_required
def get_inventory():
    """Get inventory status for a season year. Query: ?year=2026"""
    year = request.args.get('year', datetime.now().year, type=int)

    inventory = services.get_inventory(year)
    if not inventory:
        return jsonify({
            'season_year': year,
            'total_tags': 0,
            'available_tags': [],
            'available_count': 0,
        })

    available = services.get_available_tags(year)
    unavailable = TagUnavailable.query.filter_by(season_year=year).all()

    return jsonify({
        'season_year': year,
        'total_tags': inventory.total_tags,
        'available_tags': available,
        'available_count': len(available),
        'unavailable_tags': [
            {'tag_number': u.tag_number, 'reason': u.reason}
            for u in unavailable
        ],
    })


@tags_bp.route('/inventory', methods=['POST'])
@admin_required
def set_inventory():
    """
    Set or update inventory for a season year.
    Accepts {season_year, total_tags}.
    """
    data = request.get_json()
    if not data or 'total_tags' not in data:
        return jsonify({'error': 'total_tags is required'}), 400

    season_year = data.get('season_year', datetime.now().year)
    total_tags = data['total_tags']

    if not isinstance(total_tags, int) or total_tags < 1:
        return jsonify({'error': 'total_tags must be a positive integer'}), 400

    success, msg = services.set_total_tags(season_year, total_tags)
    if not success:
        return jsonify({'error': msg}), 400

    return jsonify({'message': msg, 'season_year': season_year, 'total_tags': total_tags})


@tags_bp.route('/inventory/unavailable', methods=['POST'])
@admin_required
def mark_tag_unavailable():
    """Mark a tag as lost/unavailable. Accepts {season_year, tag_number, reason}."""
    data = request.get_json()
    if not data or 'tag_number' not in data:
        return jsonify({'error': 'tag_number is required'}), 400

    season_year = data.get('season_year', datetime.now().year)
    tag_number = data['tag_number']
    reason = data.get('reason')

    success, msg = services.mark_tag_unavailable(season_year, tag_number, reason)
    if not success:
        return jsonify({'error': msg}), 400

    return jsonify({'message': msg})


@tags_bp.route('/inventory/unavailable', methods=['DELETE'])
@admin_required
def restore_tag_available():
    """Restore a previously unavailable tag. Accepts {season_year, tag_number}."""
    data = request.get_json()
    if not data or 'tag_number' not in data:
        return jsonify({'error': 'tag_number is required'}), 400

    season_year = data.get('season_year', datetime.now().year)
    tag_number = data['tag_number']

    success, msg = services.mark_tag_available(season_year, tag_number)
    if not success:
        return jsonify({'error': msg}), 400

    return jsonify({'message': msg})


@tags_bp.route('/members/<int:member_id>/assign-tag', methods=['POST'])
@login_required
def assign_tag(member_id):
    """
    Assign a tag to a member outside of an event (new membership purchase).
    Accepts {season_year, tag_number (optional — defaults to lowest available)}.
    """
    data = request.get_json() or {}
    season_year = data.get('season_year', datetime.now().year)
    tag_number = data.get('tag_number')  # None = lowest available

    success, msg = services.assign_tag_to_member(member_id, season_year, tag_number)
    if not success:
        return jsonify({'error': msg}), 400

    member = TagMember.query.get(member_id)
    return jsonify({
        'message': msg,
        'member_id': member_id,
        'current_tag': member.current_tag if member else None,
    })


# ═══════════════════════════════════════════════════════════════════════════════
# Standings & History
# ═══════════════════════════════════════════════════════════════════════════════

@tags_bp.route('/standings', methods=['GET'])
def get_standings():
    """Get current tag standings."""
    return jsonify(services.get_current_standings())


@tags_bp.route('/members/<int:member_id>/history', methods=['GET'])
def get_member_history(member_id):
    """Get tag history for a specific member."""
    member = TagMember.query.get(member_id)
    if not member:
        return jsonify({'error': 'Member not found'}), 404

    history = services.get_member_history(member_id)
    return jsonify(history)


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _log_pii_access(member_id: int, action: str):
    """Log PII access for audit trail."""
    user_id = session.get('user_id')
    if user_id:
        log = PiiAccessLog(user_id=user_id, member_id=member_id, action=action)
        db.session.add(log)
