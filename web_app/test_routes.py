#!/usr/bin/env python3
"""
Test script for the web application routes.
"""

from app import app

def list_routes():
    """List all available routes in the Flask application."""
    print('Available routes:')
    for rule in app.url_map.iter_rules():
        print(f'  {rule.endpoint}: {rule.rule}')

if __name__ == '__main__':
    list_routes()
