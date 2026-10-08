"""
DG-Rater Platform — Flask Application Factory

Serves both DG-Dubs and DG-Tags APIs from a single Flask application.
"""

import os
import sys

from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Ensure project root is on Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

load_dotenv()


def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.secret_key = os.environ.get('SECRET_KEY', 'dev_key_for_testing_change_in_production')

    CORS(app, supports_credentials=True, origins=[
        'http://localhost:3000', 'http://127.0.0.1:3000',
        'https://dg-rater.com', 'https://tags.dg-rater.com',
    ])

    # ── Database configuration ───────────────────────────────────────
    DATABASE_URL = os.environ.get('DATABASE_URL') or \
        f"mysql+pymysql://{os.environ.get('DB_USER', 'root')}:" \
        f"{os.environ.get('DB_PASSWORD', 'password')}@" \
        f"{os.environ.get('DB_HOST', '127.0.0.1')}:" \
        f"{os.environ.get('DB_PORT', '3306')}/" \
        f"{os.environ.get('DB_NAME', 'dg_dubs')}"

    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # ── Initialize extensions ────────────────────────────────────────
    from backend.models import db
    db.init_app(app)

    # Flask-Migrate / Alembic: migrations are the source of truth for schema.
    # Set USE_DB_CREATE_ALL=true only for throwaway/test databases (e.g. the
    # in-memory SQLite used by the pytest suite).
    from flask_migrate import Migrate
    Migrate(app, db)

    # Org-scoping layer: stamp/validate org_id on tenant writes.
    from backend.shared.scoping import init_scoping
    init_scoping(app, db)

    # Resolve the current org early in each request (Phase 1: defaults to SVDGC).
    from backend.shared.org_context import resolve_org_id

    @app.before_request
    def _resolve_current_org():
        resolve_org_id()

    use_create_all = os.environ.get('USE_DB_CREATE_ALL', '').lower() in ('1', 'true', 'yes') \
        or app.config['SQLALCHEMY_DATABASE_URI'].startswith('sqlite')

    with app.app_context():
        # Import all models so create_all / Alembic autogenerate discover them
        import backend.models  # noqa: F401
        if use_create_all:
            db.create_all()

        # ── DG-Dubs services ─────────────────────────────────────────
        from backend.apps.dubs.services.ratings import TournamentRatingSystem
        from backend.shared.auth import AuthManager

        auth_manager = AuthManager()
        app.auth_manager = auth_manager

        # Boot-time DB initialization (loading ratings, seeding admin) requires
        # a migrated schema. Guard it so the app object can still be constructed
        # when the DB is not yet migrated — e.g. under `flask db ...` commands or
        # a fresh environment before `flask db upgrade` has run.
        rating_system = TournamentRatingSystem()
        try:
            rating_system.load_data()

            from backend.models import User, Organization, OrgRole
            from backend.shared.org_context import DEFAULT_ORG_ID, DEFAULT_ORG_SLUG
            admin_user = os.environ.get('ADMIN_USERNAME')
            admin_pass = os.environ.get('ADMIN_PASSWORD')
            if admin_user and admin_pass:
                if User.query.filter_by(role='admin').count() == 0:
                    success, msg = auth_manager.create_user(admin_user, admin_pass, 'admin')
                    if success:
                        print(f"Admin user '{admin_user}' created successfully")
                        # The seeded admin needs governance power in the default
                        # org, otherwise org-aware auth would 403 them on every
                        # route. Ensure the default org exists, then grant the
                        # org-wide 'owner' role (§13.6) — the admin's all-apps
                        # power is derived from this governance role, so no
                        # per-app membership rows are seeded.
                        org = db.session.get(Organization, DEFAULT_ORG_ID)
                        if org is None:
                            org = Organization(
                                org_id=DEFAULT_ORG_ID, slug=DEFAULT_ORG_SLUG,
                                name='Silicon Valley Disc Golf Club', is_active=True,
                            )
                            db.session.add(org)
                            db.session.flush()
                        new_admin = User.query.filter_by(username=admin_user).first()
                        if new_admin and OrgRole.query.filter_by(
                            org_id=DEFAULT_ORG_ID, user_id=new_admin.id
                        ).first() is None:
                            db.session.add(OrgRole(
                                org_id=DEFAULT_ORG_ID, user_id=new_admin.id,
                                role='owner',
                            ))
                        db.session.commit()
        except Exception as exc:  # noqa: BLE001 — tolerate unmigrated/unavailable DB at construction
            app.logger.warning(
                "Skipping DB-dependent boot init (DB not ready?): %s", exc
            )
        app.rating_system = rating_system

    # ── Register blueprints ──────────────────────────────────────────

    # DG-Dubs routes
    from backend.apps.dubs.routes import dubs_blueprints
    for blueprint in dubs_blueprints:
        app.register_blueprint(blueprint)

    # DG-Tags routes
    from backend.apps.tags.routes import tags_bp
    app.register_blueprint(tags_bp)

    # ── Health check ─────────────────────────────────────────────────

    @app.route('/')
    def health_check():
        return jsonify({
            "status": "DG-Rater Platform API is running",
            "apps": ["dubs", "tags"],
        })

    return app


# Allow running directly: python backend/app.py
if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
