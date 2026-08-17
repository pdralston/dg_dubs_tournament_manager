"""DG-Tags Service Layer

Implements the bag tag distribution algorithm, inventory management,
event lifecycle state transitions, and member management.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional, Set, Tuple

from backend.models import (
    db, TagMember, TagEvent, TagRegistration, TagHistory,
    TagInventory, TagUnavailable,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Inventory Management
# ═══════════════════════════════════════════════════════════════════════════════

def get_inventory(season_year: int) -> Optional[TagInventory]:
    """Get the inventory record for a season year."""
    return TagInventory.query.filter_by(season_year=season_year).first()


def get_or_create_inventory(season_year: int, total_tags: int) -> TagInventory:
    """Get or create an inventory record for a season year."""
    inventory = get_inventory(season_year)
    if not inventory:
        inventory = TagInventory(season_year=season_year, total_tags=total_tags)
        db.session.add(inventory)
        db.session.flush()
    return inventory


def set_total_tags(season_year: int, total_tags: int) -> Tuple[bool, str]:
    """
    Set the total tags for a season. Validates that total_tags is not
    lower than the highest tag currently assigned.
    """
    highest_assigned = _get_highest_assigned_tag(season_year)
    if total_tags < highest_assigned:
        return False, (
            f"Cannot set total_tags to {total_tags}. "
            f"Highest currently assigned tag is {highest_assigned}."
        )

    inventory = get_inventory(season_year)
    if inventory:
        inventory.total_tags = total_tags
    else:
        inventory = TagInventory(season_year=season_year, total_tags=total_tags)
        db.session.add(inventory)

    db.session.commit()
    return True, f"Total tags for {season_year} set to {total_tags}."


def get_available_tags(season_year: int) -> List[int]:
    """
    Get all available (unissued, not lost) tag numbers for a season.
    Available = {1..total_tags} - assigned - unavailable
    """
    inventory = get_inventory(season_year)
    if not inventory:
        return []

    all_tags = set(range(1, inventory.total_tags + 1))
    assigned = _get_assigned_tags()
    unavailable = _get_unavailable_tags(season_year)

    available = sorted(all_tags - assigned - unavailable)
    return available


def get_lowest_available_tag(season_year: int) -> Optional[int]:
    """Get the lowest available tag number from inventory."""
    available = get_available_tags(season_year)
    return available[0] if available else None


def get_highest_available_tags(season_year: int, count: int) -> List[int]:
    """Get the N highest available tag numbers from inventory, descending."""
    available = get_available_tags(season_year)
    return sorted(available[-count:], reverse=True) if len(available) >= count else sorted(available, reverse=True)


def mark_tag_unavailable(season_year: int, tag_number: int, reason: str = None) -> Tuple[bool, str]:
    """Mark a specific tag number as lost/unavailable."""
    inventory = get_inventory(season_year)
    if not inventory:
        return False, f"No inventory record for season {season_year}."

    if tag_number < 1 or tag_number > inventory.total_tags:
        return False, f"Tag {tag_number} is outside inventory range (1-{inventory.total_tags})."

    # Check if already unavailable
    existing = TagUnavailable.query.filter_by(
        season_year=season_year, tag_number=tag_number
    ).first()
    if existing:
        return False, f"Tag {tag_number} is already marked unavailable."

    # Check if assigned to a member
    assigned = _get_assigned_tags()
    if tag_number in assigned:
        return False, f"Tag {tag_number} is currently assigned to a member. Remove assignment first."

    entry = TagUnavailable(
        season_year=season_year,
        tag_number=tag_number,
        reason=reason
    )
    db.session.add(entry)
    db.session.commit()
    return True, f"Tag {tag_number} marked as unavailable."


def mark_tag_available(season_year: int, tag_number: int) -> Tuple[bool, str]:
    """Restore a previously unavailable tag to available status."""
    entry = TagUnavailable.query.filter_by(
        season_year=season_year, tag_number=tag_number
    ).first()
    if not entry:
        return False, f"Tag {tag_number} is not marked as unavailable."

    db.session.delete(entry)
    db.session.commit()
    return True, f"Tag {tag_number} restored to available."


def assign_tag_to_member(member_id: int, season_year: int, tag_number: int = None) -> Tuple[bool, str]:
    """
    Assign a tag to a member (outside of an event context).
    If tag_number is None, assigns the lowest available.
    """
    member = TagMember.query.get(member_id)
    if not member:
        return False, "Member not found."

    available = get_available_tags(season_year)
    if not available:
        return False, "No tags available in inventory."

    if tag_number is None:
        tag_number = available[0]  # Lowest available
    elif tag_number not in available:
        return False, f"Tag {tag_number} is not available (already assigned or marked unavailable)."

    member.current_tag = tag_number
    db.session.commit()
    return True, f"Tag {tag_number} assigned to {member.name}."


# ═══════════════════════════════════════════════════════════════════════════════
# Event State Transitions
# ═══════════════════════════════════════════════════════════════════════════════

def transition_to_scheduled(event_id: int) -> Tuple[bool, str]:
    """
    Pending → Scheduled: All pre-registrations are complete.
    Event becomes visible to unauthenticated users.
    """
    event = TagEvent.query.get(event_id)
    if not event:
        return False, "Event not found."
    if not event.can_transition_to('scheduled'):
        return False, f"Cannot transition from '{event.status}' to 'scheduled'."

    event.status = 'scheduled'
    db.session.commit()
    return True, "Event is now scheduled and visible to all users."


def transition_to_in_progress(event_id: int, season_year: int) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Scheduled → In Progress: Triggers automated actions:
    1. Non-player tag assignment (Annual only)
    2. DNF assignment for unchecked players

    Returns (success, message, details_dict).
    """
    event = TagEvent.query.get(event_id)
    if not event:
        return False, "Event not found.", {}
    if not event.can_transition_to('in_progress'):
        return False, f"Cannot transition from '{event.status}' to 'in_progress'.", {}

    details = {'dnf_players': [], 'non_player_assignments': []}

    registrations = TagRegistration.query.filter_by(event_id=event_id).all()

    # 1. Mark unchecked players as DNF
    for reg in registrations:
        if reg.is_player and not reg.is_checked_in:
            reg.is_dnf = True
            member = TagMember.query.get(reg.member_id)
            details['dnf_players'].append({
                'member_id': reg.member_id,
                'name': member.name if member else 'Unknown',
                'old_tag': reg.old_tag,
            })

    # 2. Assign tags to non-players (Annual events only)
    if event.event_type == 'annual':
        non_player_results = _assign_non_player_tags(event_id, season_year)
        details['non_player_assignments'] = non_player_results

    event.status = 'in_progress'
    db.session.commit()
    return True, "Event is now in progress.", details


def transition_to_complete(event_id: int, season_year: int) -> Tuple[bool, str, List[Dict[str, Any]]]:
    """
    In Progress → Complete: Run tag distribution and finalize results.
    Returns (success, message, results_list).
    """
    event = TagEvent.query.get(event_id)
    if not event:
        return False, "Event not found.", []
    if not event.can_transition_to('complete'):
        return False, f"Cannot transition from '{event.status}' to 'complete'.", []

    # Run distribution algorithm
    results = compute_tag_distribution(event_id, event.event_type)
    if not results:
        return False, "No players with scores found. Cannot complete event.", []

    # Write history entries
    _write_history(event_id, results)

    # Update member current_tag values
    for result in results:
        if result['new_tag'] is not None:
            member = TagMember.query.get(result['member_id'])
            if member:
                member.current_tag = result['new_tag']

    event.status = 'complete'
    db.session.commit()
    return True, "Event completed. Tags distributed.", results


# ═══════════════════════════════════════════════════════════════════════════════
# Tag Distribution Algorithm
# ═══════════════════════════════════════════════════════════════════════════════

def compute_tag_distribution(event_id: int, event_type: str) -> List[Dict[str, Any]]:
    """
    Compute tag redistribution for an event.

    Monthly:
      - Pool = set of old_tag values from all registered players (including DNF)
      - Finished players sorted by score ASC, old_tag ASC
      - DNF players get highest tags, ordered by old_tag DESC

    Annual:
      - Pool = 1..n where n = number of checked-in players
      - Finished players sorted by score ASC, old_tag ASC (prev year's tag)
      - DNF players get highest tags, ordered by old_tag DESC
    """
    registrations = TagRegistration.query.filter_by(event_id=event_id).all()

    # Only consider player registrations (not non-players)
    player_regs = [r for r in registrations if r.is_player]
    if not player_regs:
        return []

    # Determine the tag pool
    if event_type == 'monthly':
        # Pool = turned-in tags from all players (including DNF)
        available_tags = sorted([r.old_tag for r in player_regs if r.old_tag is not None])
    else:
        # Annual: pool = 1..n where n = checked-in players
        checked_in_count = len([r for r in player_regs if r.is_checked_in])
        available_tags = list(range(1, checked_in_count + 1))

    if not available_tags:
        return []

    # Separate finished players from DNF players
    finished = [r for r in player_regs if r.round_score is not None and not r.is_dnf]
    dnf_players = [r for r in player_regs if r.is_dnf]

    # Sort DNF players by old_tag descending (highest prev tag gets highest available tag)
    dnf_players.sort(key=lambda r: (r.old_tag or 0), reverse=True)

    # Assign highest tags to DNF players
    dnf_tags = available_tags[-len(dnf_players):] if dnf_players else []
    dnf_tags.sort(reverse=True)  # Highest first to match with highest prev tag

    # Remaining tags for finished players
    remaining_tags = available_tags[:len(available_tags) - len(dnf_players)]

    # Sort finished players by score ASC, then old_tag ASC (tiebreaker)
    finished.sort(key=lambda r: (r.round_score, r.old_tag or 0))

    results = []

    # Assign tags to finished players
    for position, (reg, new_tag) in enumerate(zip(finished, remaining_tags), start=1):
        reg.new_tag = new_tag
        reg.position = position
        member = TagMember.query.get(reg.member_id)
        results.append({
            'member_id': reg.member_id,
            'name': member.name if member else 'Unknown',
            'old_tag': reg.old_tag,
            'new_tag': new_tag,
            'round_score': reg.round_score,
            'is_dnf': False,
            'position': position,
        })

    # Assign tags to DNF players
    dnf_start_position = len(finished) + 1
    for i, (reg, new_tag) in enumerate(zip(dnf_players, dnf_tags)):
        position = dnf_start_position + i
        reg.new_tag = new_tag
        reg.position = position
        reg.is_dnf = True
        member = TagMember.query.get(reg.member_id)
        results.append({
            'member_id': reg.member_id,
            'name': member.name if member else 'Unknown',
            'old_tag': reg.old_tag,
            'new_tag': new_tag,
            'round_score': reg.round_score,
            'is_dnf': True,
            'position': position,
        })

    db.session.flush()
    return results


# ═══════════════════════════════════════════════════════════════════════════════
# Member Management
# ═══════════════════════════════════════════════════════════════════════════════

def search_members(query: str) -> List[Dict[str, Any]]:
    """
    Search members by name or UDisc name (case-insensitive partial match).
    Used for Monthly same-day registration to find existing members.
    """
    search_term = f"%{query}%"
    members = TagMember.query.filter(
        db.and_(
            TagMember.is_active == True,  # noqa: E712
            db.or_(
                TagMember.name.ilike(search_term),
                TagMember.udisc_name.ilike(search_term),
            )
        )
    ).order_by(TagMember.name).limit(20).all()

    return [
        {
            'member_id': m.member_id,
            'name': m.name,
            'udisc_name': m.udisc_name,
            'current_tag': m.current_tag,
        }
        for m in members
    ]


def check_duplicate_member(name: str, udisc_name: str = None) -> List[Dict[str, Any]]:
    """
    Check for potential duplicate members based on name/udisc_name.
    Returns a list of potential matches for TD/Admin to review.
    """
    candidates = []

    # Exact name match
    exact_name = TagMember.query.filter(
        db.and_(
            TagMember.is_active == True,  # noqa: E712
            db.func.lower(TagMember.name) == name.lower()
        )
    ).all()
    candidates.extend(exact_name)

    # UDisc name match
    if udisc_name:
        udisc_matches = TagMember.query.filter(
            db.and_(
                TagMember.is_active == True,  # noqa: E712
                db.func.lower(TagMember.udisc_name) == udisc_name.lower()
            )
        ).all()
        for m in udisc_matches:
            if m not in candidates:
                candidates.append(m)

    # Fuzzy partial match on name
    name_parts = name.lower().split()
    if len(name_parts) >= 2:
        # Check if first+last appear in existing members
        for part in name_parts:
            partial = TagMember.query.filter(
                db.and_(
                    TagMember.is_active == True,  # noqa: E712
                    TagMember.name.ilike(f"%{part}%")
                )
            ).limit(10).all()
            for m in partial:
                if m not in candidates:
                    candidates.append(m)

    return [
        {
            'member_id': m.member_id,
            'name': m.name,
            'udisc_name': m.udisc_name,
            'current_tag': m.current_tag,
        }
        for m in candidates[:10]  # Cap at 10 results
    ]


def match_udisc_results(
    results_data: List[Dict[str, Any]],
    event_id: int
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Match imported UDisc results to checked-in players.
    Returns (matched, unmatched) where:
      - matched: [{member_id, name, udisc_name, round_score}]
      - unmatched: [{udisc_name, round_score, candidates: [...]}]
    """
    registrations = TagRegistration.query.filter_by(event_id=event_id).filter(
        TagRegistration.is_player == True,  # noqa: E712
        TagRegistration.is_checked_in == True  # noqa: E712
    ).all()

    # Build lookup by udisc_name (case-insensitive)
    reg_by_udisc = {}
    reg_by_name = {}
    for reg in registrations:
        member = TagMember.query.get(reg.member_id)
        if member:
            if member.udisc_name:
                reg_by_udisc[member.udisc_name.lower()] = (reg, member)
            reg_by_name[member.name.lower()] = (reg, member)

    matched = []
    unmatched = []

    for result in results_data:
        udisc_name = result.get('name', '').strip()
        score = result.get('total_score') or result.get('round_score')
        if score is None:
            continue

        # Try exact UDisc name match
        lookup_key = udisc_name.lower()
        if lookup_key in reg_by_udisc:
            reg, member = reg_by_udisc[lookup_key]
            matched.append({
                'member_id': member.member_id,
                'reg_id': reg.reg_id,
                'name': member.name,
                'udisc_name': udisc_name,
                'round_score': int(score),
            })
            continue

        # Try exact name match
        if lookup_key in reg_by_name:
            reg, member = reg_by_name[lookup_key]
            matched.append({
                'member_id': member.member_id,
                'reg_id': reg.reg_id,
                'name': member.name,
                'udisc_name': udisc_name,
                'round_score': int(score),
            })
            continue

        # No match found — provide candidates for manual resolution
        candidates = []
        for reg in registrations:
            member = TagMember.query.get(reg.member_id)
            if member:
                # Simple fuzzy: check if any word in the import name appears in member name
                import_words = set(udisc_name.lower().split())
                member_words = set(member.name.lower().split())
                udisc_words = set((member.udisc_name or '').lower().split())
                overlap = import_words & (member_words | udisc_words)
                if overlap:
                    candidates.append({
                        'member_id': member.member_id,
                        'reg_id': reg.reg_id,
                        'name': member.name,
                        'udisc_name': member.udisc_name,
                    })

        unmatched.append({
            'import_name': udisc_name,
            'round_score': int(score),
            'candidates': candidates,
        })

    return matched, unmatched


# ═══════════════════════════════════════════════════════════════════════════════
# Standings & History
# ═══════════════════════════════════════════════════════════════════════════════

def get_current_standings() -> List[Dict[str, Any]]:
    """Get current tag standings (all active members sorted by tag number)."""
    members = TagMember.query.filter_by(is_active=True).filter(
        TagMember.current_tag.isnot(None)
    ).order_by(TagMember.current_tag).all()

    return [
        {
            'member_id': m.member_id,
            'name': m.name,
            'udisc_name': m.udisc_name,
            'current_tag': m.current_tag,
        }
        for m in members
    ]


def get_member_history(member_id: int) -> List[Dict[str, Any]]:
    """Get tag history for a specific member."""
    history = TagHistory.query.filter_by(member_id=member_id).join(
        TagEvent, TagHistory.event_id == TagEvent.event_id
    ).order_by(TagEvent.date.desc()).all()

    return [
        {
            'history_id': h.history_id,
            'event_id': h.event_id,
            'date': h.event.date.isoformat(),
            'course': h.event.course,
            'event_type': h.event.event_type,
            'old_tag': h.old_tag,
            'new_tag': h.new_tag,
            'round_score': h.round_score,
            'is_dnf': h.is_dnf,
            'position': h.position,
        }
        for h in history
    ]


# ═══════════════════════════════════════════════════════════════════════════════
# Import Helpers
# ═══════════════════════════════════════════════════════════════════════════════

def parse_registration_csv(file_content: str) -> List[Dict[str, Any]]:
    """
    Parse a DGScene registration CSV file into a list of member dicts.
    Expected headers: Division, Name, First name, Last name, PDGA#, Email,
    Phone, Entry fee $, Last Year's Tag, Address, City, State, ZIP, Country,
    Registration date PST, Notes

    Returns list of dicts with normalized keys.
    """
    import csv
    import io

    reader = csv.DictReader(io.StringIO(file_content))
    members = []

    for row in reader:
        # Skip empty rows
        name = row.get('Name', '').strip()
        if not name:
            continue

        # Determine if this is a player based on division
        # Convention: non-player divisions will vary by org, but
        # we expose is_player for the TD to confirm/override
        division = row.get('Division', '').strip()

        # Build address from components
        address_parts = [
            row.get('Address', '').strip(),
            row.get('City', '').strip(),
            row.get('State', '').strip(),
            row.get('ZIP', '').strip(),
            row.get('Country', '').strip(),
        ]
        shipping_address = ', '.join(p for p in address_parts if p)

        # Parse previous tag
        prev_tag_raw = row.get("Last Year's Tag", '').strip()
        prev_tag = None
        if prev_tag_raw:
            try:
                prev_tag = int(prev_tag_raw)
            except ValueError:
                pass

        members.append({
            'name': name,
            'division': division,
            'email': row.get('Email', '').strip() or None,
            'phone': row.get('Phone', '').strip() or None,
            'shipping_address': shipping_address or None,
            'pdga_number': row.get('PDGA#', '').strip() or None,
            'previous_tag': prev_tag,
            'notes': row.get('Notes', '').strip() or None,
        })

    return members


def parse_results_file(file_content: bytes, filename: str) -> List[Dict[str, Any]]:
    """
    Parse a UDisc results file (CSV or XLSX) into a list of score dicts.
    Returns list of {name, total_score}.
    """
    if filename.lower().endswith('.xlsx'):
        return _parse_results_xlsx(file_content)
    else:
        return _parse_results_csv(file_content)


def _parse_results_csv(file_content: bytes) -> List[Dict[str, Any]]:
    """Parse a UDisc CSV results file."""
    import csv
    import io

    text = file_content.decode('utf-8-sig')  # Handle BOM
    reader = csv.DictReader(io.StringIO(text))
    results = []

    for row in reader:
        name = None
        score = None

        # UDisc CSV headers vary; look for common patterns
        for key in ('Name', 'PlayerName', 'Player Name', 'Player'):
            if key in row and row[key].strip():
                name = row[key].strip()
                break

        for key in ('Total', 'Total Score', 'Score', '+/-', 'Par'):
            if key in row and row[key].strip():
                try:
                    score = int(row[key].strip())
                    break
                except ValueError:
                    continue

        if name and score is not None:
            results.append({'name': name, 'total_score': score})

    return results


def _parse_results_xlsx(file_content: bytes) -> List[Dict[str, Any]]:
    """Parse a UDisc XLSX results file."""
    import io

    try:
        import openpyxl
    except ImportError:
        raise ImportError("openpyxl is required for XLSX file support. Install with: pip install openpyxl")

    wb = openpyxl.load_workbook(io.BytesIO(file_content), read_only=True)
    ws = wb.active
    results = []

    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return []

    # Find header row
    headers = [str(cell).strip() if cell else '' for cell in rows[0]]

    # Find name and score columns
    name_col = None
    score_col = None

    for i, h in enumerate(headers):
        h_lower = h.lower()
        if h_lower in ('name', 'playername', 'player name', 'player'):
            name_col = i
        elif h_lower in ('total', 'total score', 'score', '+/-', 'par'):
            score_col = i

    if name_col is None or score_col is None:
        # Try to infer: first string column = name, last numeric column = score
        for i, h in enumerate(headers):
            if name_col is None and h and not h.replace('-', '').replace('+', '').isdigit():
                name_col = i
            if h and (h.replace('-', '').replace('+', '').isdigit() or h_lower in ('total',)):
                score_col = i

    if name_col is None or score_col is None:
        return []

    for row in rows[1:]:
        if len(row) <= max(name_col, score_col):
            continue

        name = str(row[name_col]).strip() if row[name_col] else None
        score_raw = row[score_col]

        if not name or score_raw is None:
            continue

        try:
            score = int(score_raw)
        except (ValueError, TypeError):
            continue

        results.append({'name': name, 'total_score': score})

    wb.close()
    return results


# ═══════════════════════════════════════════════════════════════════════════════
# Private Helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _get_assigned_tags() -> Set[int]:
    """Get set of all tag numbers currently assigned to active members."""
    members = TagMember.query.filter(
        TagMember.is_active == True,  # noqa: E712
        TagMember.current_tag.isnot(None)
    ).all()
    return {m.current_tag for m in members}


def _get_unavailable_tags(season_year: int) -> Set[int]:
    """Get set of tag numbers marked as unavailable for a season."""
    entries = TagUnavailable.query.filter_by(season_year=season_year).all()
    return {e.tag_number for e in entries}


def _get_highest_assigned_tag(season_year: int) -> int:
    """Get the highest tag number currently assigned to any active member."""
    result = db.session.query(db.func.max(TagMember.current_tag)).filter(
        TagMember.is_active == True  # noqa: E712
    ).scalar()
    return result or 0


def _assign_non_player_tags(event_id: int, season_year: int) -> List[Dict[str, Any]]:
    """
    Assign tags to non-player registrants from highest available.
    Order:
    1. Non-players without previous tag — first, highest available, no order
    2. Non-players with previous tag — remaining highest available,
       ordered by previous tag descending
    """
    non_player_regs = TagRegistration.query.filter_by(
        event_id=event_id, is_player=False
    ).all()

    if not non_player_regs:
        return []

    # Split into those with and without previous tags
    no_prev_tag = [r for r in non_player_regs if not r.old_tag]
    has_prev_tag = [r for r in non_player_regs if r.old_tag]

    # Sort those with previous tags by prev tag descending
    has_prev_tag.sort(key=lambda r: r.old_tag, reverse=True)

    # Total non-players to assign
    total_needed = len(non_player_regs)

    # Get highest available tags
    available = get_highest_available_tags(season_year, total_needed)
    if len(available) < total_needed:
        # Not enough tags available — assign what we can
        available = get_highest_available_tags(season_year, len(available))

    results = []
    tag_idx = 0

    # 1. Assign to non-players without previous tags first (highest available, no order)
    for reg in no_prev_tag:
        if tag_idx >= len(available):
            break
        tag = available[tag_idx]
        tag_idx += 1
        reg.new_tag = tag
        # Update member's current tag
        member = TagMember.query.get(reg.member_id)
        if member:
            member.current_tag = tag
        results.append({
            'member_id': reg.member_id,
            'name': member.name if member else 'Unknown',
            'new_tag': tag,
            'previous_tag': reg.old_tag,
        })

    # 2. Assign to non-players with previous tags (highest prev → highest available)
    for reg in has_prev_tag:
        if tag_idx >= len(available):
            break
        tag = available[tag_idx]
        tag_idx += 1
        reg.new_tag = tag
        member = TagMember.query.get(reg.member_id)
        if member:
            member.current_tag = tag
        results.append({
            'member_id': reg.member_id,
            'name': member.name if member else 'Unknown',
            'new_tag': tag,
            'previous_tag': reg.old_tag,
        })

    db.session.flush()
    return results


def _write_history(event_id: int, results: List[Dict[str, Any]]) -> None:
    """Write TagHistory entries for finalized results."""
    for r in results:
        history = TagHistory(
            member_id=r['member_id'],
            event_id=event_id,
            old_tag=r['old_tag'],
            new_tag=r['new_tag'],
            round_score=r['round_score'],
            is_dnf=r.get('is_dnf', False),
            position=r['position'],
        )
        db.session.add(history)
    db.session.flush()
