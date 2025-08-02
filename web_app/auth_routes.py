#!/usr/bin/env python3
"""
Authentication routes for the Disc Golf League Tournament Rating System.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from auth import login_required, is_authenticated, get_current_user

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login page and authentication handler."""
    # Redirect if already authenticated
    if is_authenticated():
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('Please enter both username and password.', 'error')
            return render_template('auth/login.html')
        
        # Get client info for security logging
        ip_address = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
        user_agent = request.headers.get('User-Agent', '')
        
        # Authenticate user
        auth_manager = current_app.auth_manager
        success, result = auth_manager.authenticate_user(
            username, password, ip_address, user_agent
        )
        
        if success:
            # Store session info
            session['session_token'] = result['session_token']
            session['user_id'] = result['user_id']
            session['username'] = result['username']
            session['role'] = result['role']
            
            flash(f'Welcome back, {result["username"]}!', 'success')
            
            # Redirect to next page or home
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('index'))
        else:
            flash(result, 'error')
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
def logout():
    """Logout handler."""
    if 'session_token' in session:
        auth_manager = current_app.auth_manager
        auth_manager.logout_user(session['session_token'])
    
    session.clear()
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('index'))

@auth_bp.route('/register', methods=['GET', 'POST'])
@login_required
def register():
    """User registration page (admin only)."""
    current_user = get_current_user()
    if not current_user or current_user['role'] != 'admin':
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        role = request.form.get('role', 'organizer')
        
        # Validation
        if not username or not password:
            flash('Username and password are required.', 'error')
            return render_template('auth/register.html')
        
        if len(username) < 3:
            flash('Username must be at least 3 characters long.', 'error')
            return render_template('auth/register.html')
        
        if len(password) < 8:
            flash('Password must be at least 8 characters long.', 'error')
            return render_template('auth/register.html')
        
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('auth/register.html')
        
        if role not in ['organizer', 'admin']:
            role = 'organizer'
        
        # Create user
        auth_manager = current_app.auth_manager
        success, message = auth_manager.create_user(username, password, role)
        
        if success:
            flash(f'User "{username}" created successfully with role "{role}".', 'success')
            return redirect(url_for('auth.register'))
        else:
            flash(message, 'error')
    
    return render_template('auth/register.html')

@auth_bp.route('/profile')
@login_required
def profile():
    """User profile page."""
    current_user = get_current_user()
    return render_template('auth/profile.html', user=current_user)
