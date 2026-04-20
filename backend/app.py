#!/usr/bin/env python3
"""
Disc Golf League Tournament Rating System - Backend API

Flask API backend backed by MySQL via SQLAlchemy.
"""

from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import os
import sys

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tournament_core.models import db, User
from tournament_core import TournamentRatingSystem
from backend.auth import AuthManager
from backend.api import all_blueprints

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev_key_for_testing_change_in_production')
CORS(app, supports_credentials=True, origins=[
    'http://localhost:3000', 'http://127.0.0.1:3000',
])

# Database configuration
DATABASE_URL = os.environ.get('DATABASE_URL') or \
    f"mysql+pymysql://{os.environ.get('DB_USER', 'root')}:" \
    f"{os.environ.get('DB_PASSWORD', 'password')}@" \
    f"{os.environ.get('DB_HOST', '127.0.0.1')}:" \
    f"{os.environ.get('DB_PORT', '3306')}/" \
    f"{os.environ.get('DB_NAME', 'dg_dubs')}"

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    db.create_all()

    rating_system = TournamentRatingSystem()
    rating_system.load_data()

    auth_manager = AuthManager()
    app.auth_manager = auth_manager
    app.rating_system = rating_system

    # Ensure admin user
    admin_user = os.environ.get('ADMIN_USERNAME')
    admin_pass = os.environ.get('ADMIN_PASSWORD')
    if admin_user and admin_pass:
        if User.query.filter_by(role='admin').count() == 0:
            success, msg = auth_manager.create_user(admin_user, admin_pass, 'admin')
            if success:
                print(f"Admin user '{admin_user}' created successfully")

for blueprint in all_blueprints:
    app.register_blueprint(blueprint)


@app.route('/')
def health_check():
    return jsonify({"status": "DG Dubs API is running"})


if __name__ == '__main__':
    app.run(debug=True)
