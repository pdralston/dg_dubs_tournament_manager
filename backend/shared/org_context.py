"""Org context resolution.

Resolves the current organization for a request into ``g.current_org_id``.

Phase 1 is single-org (SVDGC, org_id=1): resolution defaults to SVDGC. The
mechanism already reads from an explicit source order (request → session →
default) so that multi-org routing (`/<org>/<app>` URLs) can be layered in
later without touching call sites.
"""

from flask import g, session, request

# Phase 1 default org. When multi-org lands, this becomes a fallback only.
DEFAULT_ORG_ID = 1
DEFAULT_ORG_SLUG = 'svdgc'


def resolve_org_id() -> int:
    """Determine the current org id for this request and cache it on ``g``.

    Resolution order (first match wins):
      1. An org already resolved earlier in the request (``g.current_org_id``).
      2. A view arg ``org_slug`` from a ``/<org_slug>/...`` route (future).
      3. The org stored in the session at login (future multi-org).
      4. The Phase 1 default (SVDGC).
    """
    if getattr(g, 'current_org_id', None) is not None:
        return g.current_org_id

    org_id = None

    # (2) Future: path-based org slug. Resolve slug -> org_id when present.
    org_slug = (request.view_args or {}).get('org_slug') if request else None
    if org_slug:
        from backend.models import Organization
        org = Organization.query.filter_by(slug=org_slug, is_active=True).first()
        if org:
            org_id = org.org_id

    # (3) Future: session-selected org for multi-org users.
    if org_id is None:
        org_id = session.get('org_id')

    # (4) Phase 1 default.
    if org_id is None:
        org_id = DEFAULT_ORG_ID

    g.current_org_id = org_id
    return org_id


def current_org_id() -> int:
    """Return the current org id, resolving it if not already cached."""
    return resolve_org_id()
