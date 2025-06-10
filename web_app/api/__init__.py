"""
API module for the Disc Golf League Tournament Rating System.
This module provides RESTful API endpoints for the web application.
"""

from flask import Blueprint

# Import API blueprints
from .players import players_bp
from .tournaments import tournaments_bp
from .storage import storage_bp

# List of all blueprints for easy registration
all_blueprints = [players_bp, tournaments_bp, storage_bp]
