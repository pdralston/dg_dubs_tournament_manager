#!/usr/bin/env python3
"""
Authentication module for the Disc Golf League Tournament Rating System.
"""

import hashlib
import secrets
import sqlite3
import os
from functools import wraps
from flask import session, request, redirect, url_for, flash, current_app
from datetime import datetime, timedelta

class AuthManager:
    """Manages authentication and user sessions."""
    
    def __init__(self, db_file):
        self.db_file = db_file
        self.init_auth_tables()
    
    def init_auth_tables(self):
        """Initialize authentication tables in the database."""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # Create users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    role TEXT DEFAULT 'organizer',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1
                )
            """)
            
            # Create sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    session_token TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    ip_address TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """)
            
            conn.commit()
            conn.close()
            
        except sqlite3.Error as e:
            print(f"Error initializing auth tables: {e}")
    
    def hash_password(self, password, salt=None):
        """Hash a password with salt using PBKDF2."""
        if salt is None:
            salt = secrets.token_hex(32)
        
        password_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000  # 100,000 iterations
        )
        
        return password_hash.hex(), salt
    
    def verify_password(self, password, stored_hash, salt):
        """Verify a password against stored hash and salt."""
        password_hash, _ = self.hash_password(password, salt)
        return secrets.compare_digest(password_hash, stored_hash)
    
    def create_user(self, username, password, role='organizer'):
        """Create a new user account."""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # Check if username already exists
            cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
            if cursor.fetchone():
                conn.close()
                return False, "Username already exists"
            
            # Hash password
            password_hash, salt = self.hash_password(password)
            
            # Insert user
            cursor.execute("""
                INSERT INTO users (username, password_hash, salt, role)
                VALUES (?, ?, ?, ?)
            """, (username, password_hash, salt, role))
            
            conn.commit()
            conn.close()
            
            return True, "User created successfully"
            
        except sqlite3.Error as e:
            return False, f"Database error: {e}"
    
    def authenticate_user(self, username, password, ip_address=None):
        """Authenticate a user and create a session."""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            # Get user
            cursor.execute("""
                SELECT id, username, password_hash, salt, role, is_active
                FROM users WHERE username = ? AND is_active = 1
            """, (username,))
            
            user = cursor.fetchone()
            if not user:
                conn.close()
                return False, "Invalid username or password"
            
            user_id, username, stored_hash, salt, role, is_active = user
            
            # Verify password
            if not self.verify_password(password, stored_hash, salt):
                conn.close()
                return False, "Invalid username or password"
            
            # Create session token
            session_token = secrets.token_urlsafe(32)
            expires_at = datetime.now() + timedelta(hours=24)  # 24-hour session
            
            # Store session
            cursor.execute("""
                INSERT INTO user_sessions 
                (user_id, session_token, expires_at, ip_address)
                VALUES (?, ?, ?, ?)
            """, (user_id, session_token, expires_at, ip_address))
            
            # Update last login
            cursor.execute("""
                UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?
            """, (user_id,))
            
            conn.commit()
            conn.close()
            
            return True, {
                'user_id': user_id,
                'username': username,
                'role': role,
                'session_token': session_token
            }
            
        except sqlite3.Error as e:
            return False, f"Database error: {e}"
    
    def validate_session(self, session_token):
        """Validate a session token and return user info."""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT u.id, u.username, u.role, s.expires_at
                FROM users u
                JOIN user_sessions s ON u.id = s.user_id
                WHERE s.session_token = ? AND s.is_active = 1 AND u.is_active = 1
            """, (session_token,))
            
            result = cursor.fetchone()
            if not result:
                conn.close()
                return False, None
            
            user_id, username, role, expires_at = result
            
            # Check if session has expired
            expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
            if datetime.now() > expires_at:
                # Deactivate expired session
                cursor.execute("""
                    UPDATE user_sessions SET is_active = 0 
                    WHERE session_token = ?
                """, (session_token,))
                conn.commit()
                conn.close()
                return False, None
            
            conn.close()
            
            return True, {
                'user_id': user_id,
                'username': username,
                'role': role
            }
            
        except sqlite3.Error as e:
            print(f"Session validation error: {e}")
            return False, None
    
    def logout_user(self, session_token):
        """Logout a user by deactivating their session."""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE user_sessions SET is_active = 0 
                WHERE session_token = ?
            """, (session_token,))
            
            conn.commit()
            conn.close()
            
            return True
            
        except sqlite3.Error as e:
            print(f"Logout error: {e}")
            return False

# Flask decorators and helper functions
def login_required(f):
    """Decorator to require authentication for a route."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_authenticated():
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def is_authenticated():
    """Check if the current user is authenticated."""
    if 'session_token' not in session:
        return False
    
    auth_manager = current_app.auth_manager
    valid, user_info = auth_manager.validate_session(session['session_token'])
    
    if valid:
        # Store user info in session for easy access
        session['user_id'] = user_info['user_id']
        session['username'] = user_info['username']
        session['role'] = user_info['role']
        return True
    else:
        # Clear invalid session
        session.clear()
        return False

def get_current_user():
    """Get current user information if authenticated."""
    if is_authenticated():
        return {
            'user_id': session.get('user_id'),
            'username': session.get('username'),
            'role': session.get('role')
        }
    return None
