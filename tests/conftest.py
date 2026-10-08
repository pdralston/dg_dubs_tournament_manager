"""
Shared pytest fixtures for DG-Rater backend tests.

Uses an in-memory SQLite database so tests run without MySQL.
Provides authenticated client fixtures for director and admin roles.
"""

import os
import pytest

# Override DB config BEFORE any app imports
os.environ['DATABASE_URL'] = 'sqlite://'
os.environ['SECRET_KEY'] = 'test-secret-key'
os.environ.setdefault('ADMIN_USERNAME', '')
os.environ.setdefault('ADMIN_PASSWORD', '')


from backend.app import create_app
from backend.models import db as _db
from backend.models import Organization, OrgMembership, OrgRole, User
from backend.shared.org_context import DEFAULT_ORG_ID, DEFAULT_ORG_SLUG


def _ensure_default_org():
    """Seed the Phase 1 default org (SVDGC, org_id=1) if absent."""
    if Organization.query.get(DEFAULT_ORG_ID) is None:
        _db.session.add(Organization(
            org_id=DEFAULT_ORG_ID, slug=DEFAULT_ORG_SLUG,
            name='Silicon Valley Disc Golf Club', is_active=True,
        ))
        _db.session.commit()


# App axis uses per-app membership rows (no wildcard, §13). The test suite only
# exercises these three apps; seeding one row per app gives a director the same
# cross-app reach the old '*' row did, without the (removed) wildcard.
_APPS = ('dubs', 'tags', 'putt')


def _create_app_user(auth_manager, username, password, role):
    """Create a user and grant a per-app ``OrgMembership`` (admin/director) in
    the default org for every app (§13: no wildcard)."""
    auth_manager.create_user(username, password, role)
    user = User.query.filter_by(username=username).first()
    for app in _APPS:
        _db.session.add(OrgMembership(
            org_id=DEFAULT_ORG_ID, user_id=user.id, app=app, role=role,
        ))
    _db.session.commit()


def _create_owner(auth_manager, username, password):
    """Create a user and grant the org-wide governance ``owner`` role, which
    derives app-admin on every subscribed app (§13.5)."""
    auth_manager.create_user(username, password, 'admin')
    user = User.query.filter_by(username=username).first()
    _db.session.add(OrgRole(
        org_id=DEFAULT_ORG_ID, user_id=user.id, role='owner',
    ))
    _db.session.commit()


@pytest.fixture(scope='session')
def app():
    """Create the Flask application for testing (once per test session)."""
    application = create_app()
    application.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite://',
        'WTF_CSRF_ENABLED': False,
    })
    yield application


@pytest.fixture(scope='function')
def db(app):
    """Provide a clean database for each test function."""
    with app.app_context():
        _db.create_all()
        _ensure_default_org()
        yield _db
        _db.session.rollback()
        _db.drop_all()


@pytest.fixture(scope='function')
def client(app, db):
    """Unauthenticated test client."""
    return app.test_client()


@pytest.fixture(scope='function')
def director_client(app, db):
    """Test client authenticated as a director."""
    c = app.test_client()
    with app.app_context():
        _create_app_user(app.auth_manager, 'test_director', 'test_pass', 'director')

    resp = c.post('/api/auth/login', json={
        'username': 'test_director',
        'password': 'test_pass',
    })
    assert resp.status_code == 200, f"Director login failed: {resp.json}"
    return c


@pytest.fixture(scope='function')
def admin_client(app, db):
    """Test client authenticated as an admin."""
    c = app.test_client()
    with app.app_context():
        _create_owner(app.auth_manager, 'test_admin', 'test_pass')

    resp = c.post('/api/auth/login', json={
        'username': 'test_admin',
        'password': 'test_pass',
    })
    assert resp.status_code == 200, f"Admin login failed: {resp.json}"
    return c
