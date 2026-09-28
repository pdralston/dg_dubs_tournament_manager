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
        # Create a director user
        auth_manager = app.auth_manager
        auth_manager.create_user('test_director', 'test_pass', 'director')

    # Login
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
        # Create an admin user
        auth_manager = app.auth_manager
        auth_manager.create_user('test_admin', 'test_pass', 'admin')

    # Login
    resp = c.post('/api/auth/login', json={
        'username': 'test_admin',
        'password': 'test_pass',
    })
    assert resp.status_code == 200, f"Admin login failed: {resp.json}"
    return c
