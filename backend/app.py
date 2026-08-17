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

    with app.app_context():
        # Import all models so create_all discovers them
        import backend.models  # noqa: F401
        db.create_all()

        # ── DG-Dubs services ─────────────────────────────────────────
        from backend.apps.dubs.services.ratings import TournamentRatingSystem
        from backend.shared.auth import AuthManager

        rating_system = TournamentRatingSystem()
        rating_system.load_data()
        app.rating_system = rating_system

        auth_manager = AuthManager()
        app.auth_manager = auth_manager

        # Ensure admin user exists
        from backend.models import User
        admin_user = os.environ.get('ADMIN_USERNAME')
        admin_pass = os.environ.get('ADMIN_PASSWORD')
        if admin_user and admin_pass:
            if User.query.filter_by(role='admin').count() == 0:
                success, msg = auth_manager.create_user(admin_user, admin_pass, 'admin')
                if success:
                    print(f"Admin user '{admin_user}' created successfully")

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
