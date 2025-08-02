#!/usr/bin/env python3
"""
Disc Golf League Tournament Rating System - Web Application

This module provides a web interface for the tournament rating system.
"""

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, g
import os
import datetime
import sys

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from tournament_core import TournamentRatingSystem

# Import authentication
from auth import AuthManager, login_required, is_authenticated, get_current_user

# Import API blueprints
from api import all_blueprints

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev_key_for_testing_change_in_production')

# Initialize the rating system and auth manager
rating_system = TournamentRatingSystem()
auth_manager = AuthManager(rating_system.db_file if rating_system.use_db else 'tournament_data.db')

# Make auth manager available to the app
app.auth_manager = auth_manager

# Register API blueprints
for blueprint in all_blueprints:
    app.register_blueprint(blueprint)

# Context processor to make current_user available in all templates
@app.context_processor
def inject_user():
    return dict(current_user=get_current_user())

# Authentication routes
@app.route('/login', methods=['GET', 'POST'])
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
        
        # Authenticate user
        success, result = auth_manager.authenticate_user(username, password, ip_address)
        
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

@app.route('/logout')
def logout():
    """Logout handler."""
    if 'session_token' in session:
        auth_manager.logout_user(session['session_token'])
    
    session.clear()
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
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
        success, message = auth_manager.create_user(username, password, role)
        
        if success:
            flash(f'User "{username}" created successfully with role "{role}".', 'success')
            return redirect(url_for('register'))
        else:
            flash(message, 'error')
    
    return render_template('auth/register.html')

@app.route('/profile')
@login_required
def profile():
    """User profile page."""
    current_user = get_current_user()
    return render_template('auth/profile.html', user=current_user)

@app.route('/')
def index():
    """Home page with links to main features."""
    return render_template('index.html')

@app.route('/players')
def list_players():
    """List all players and their ratings."""
    players = []
    for name, data in rating_system.players.items():
        players.append({
            'name': name,
            'rating': data['rating'],
            'tournaments_played': data['tournaments_played']
        })
    
    # Sort by rating (highest first)
    players.sort(key=lambda x: x['rating'], reverse=True)
    
    return render_template('players.html', players=players)

@app.route('/player/<name>')
def player_details(name):
    """Show details for a specific player."""
    try:
        player_data = rating_system.get_player(name)
        history = player_data.get('history', [])
        
        # Sort history by date (newest first)
        history.sort(key=lambda x: x['tournament_date'], reverse=True)
        
        return render_template('player_details.html', 
                              name=name, 
                              rating=player_data['rating'],
                              tournaments_played=player_data['tournaments_played'],
                              history=history)
    except ValueError:
        flash(f"Player {name} not found", "error")
        return redirect(url_for('list_players'))

@app.route('/add_player', methods=['GET', 'POST'])
@login_required
def add_player():
    """Add a new player."""
    if request.method == 'POST':
        name = request.form.get('name')
        rating = request.form.get('rating')
        
        if not name:
            flash("Player name is required", "error")
            return render_template('add_player.html')
        
        try:
            rating = float(rating) if rating else 1000
            rating_system.add_player(name, rating)
            flash(f"Added player {name} with initial rating {rating}", "success")
            return redirect(url_for('list_players'))
        except ValueError as e:
            flash(str(e), "error")
            return render_template('add_player.html')
    
    return render_template('add_player.html')

@app.route('/generate_teams', methods=['GET', 'POST'])
def generate_teams():
    """Generate balanced teams."""
    # Redirect to event_registration
    return redirect(url_for('event_registration'))

@app.route('/event_registration', methods=['GET', 'POST'])
@login_required
def event_registration():
    """Event registration and team generation."""
    if request.method == 'POST':
        selected_players = request.form.getlist('players')
        allow_ghost = 'allow_ghost' in request.form
        
        if len(selected_players) < 2:
            flash("Select at least 2 players", "error")
            return render_template('event_registration.html', 
                                  players=list(rating_system.players.keys()),
                                  ace_pot=rating_system.ace_pot_manager.get_balance())
        
        # First, process all new players to ensure they're in the database
        new_players_added = []
        for player_name in selected_players:
            is_new_player = request.form.get(f'is_new_player_{player_name}') == 'true'
            if is_new_player:
                rating = float(request.form.get(f'rating_{player_name}', 1000))
                is_club_member = request.form.get(f'club_member_{player_name}') == 'on'
                
                try:
                    # Check if player already exists
                    if player_name.lower() in [p.lower() for p in rating_system.players.keys()]:
                        print(f"Player {player_name} already exists, skipping add")
                    else:
                        print(f"Adding new player {player_name} with rating {rating}")
                        rating_system.add_player(player_name, rating, is_club_member)
                        new_players_added.append(player_name)
                except ValueError as e:
                    flash(str(e), "error")
                    return render_template('event_registration.html', 
                                          players=list(rating_system.players.keys()),
                                          ace_pot=rating_system.ace_pot_manager.get_balance(),
                                          ace_pot_config=rating_system.ace_pot_manager.get_config())
        
        # If new players were added, reload the player list to ensure they're in memory
        if new_players_added:
            print(f"Added {len(new_players_added)} new players: {', '.join(new_players_added)}")
            # Force a reload of player data from the database
            if rating_system.use_db:
                rating_system._load_from_db()
        
        # Now process club membership for existing players
        for player_name in selected_players:
            is_new_player = request.form.get(f'is_new_player_{player_name}') == 'true'
            if not is_new_player:  # Only update existing players
                is_club_member = request.form.get(f'club_member_{player_name}') == 'on'
                try:
                    rating_system.update_player_club_membership(player_name, is_club_member)
                except Exception as e:
                    print(f"Error updating club membership for {player_name}: {e}")
                    # Continue processing, don't stop for club membership errors
            
            # Process ace pot buy-ins
            ace_pot_buy_ins = []
            for player_name in selected_players:
                ace_pot_buy_in = request.form.get(f'ace_pot_{player_name}') == 'on'
                if ace_pot_buy_in:
                    ace_pot_buy_ins.append(player_name)
            
            # Store ace pot buy-ins in session for later processing
            if ace_pot_buy_ins:
                session['ace_pot_buy_ins'] = ace_pot_buy_ins
                print(f"Stored ace pot buy-ins for {len(ace_pot_buy_ins)} players in session")
            
            try:
                teams = rating_system.generate_balanced_teams(selected_players, allow_ghost=True)
                predictions = rating_system.predict_tournament_outcome([tuple(team) for team in teams])
                
                # Format for template
                team_data = []
                for i, team in enumerate(teams):
                    team_tuple = tuple(team)
                    team_data.append({
                        'players': team,
                        'rating': rating_system.calculate_team_rating(team[0], team[1]),
                        'expected_position': predictions[team_tuple].get('expected_position', 0)
                    })
                
                return render_template('team_results.html', teams=team_data)
            except ValueError as e:
                flash(str(e), "error")
                return render_template('event_registration.html', 
                                      players=list(rating_system.players.keys()),
                                      ace_pot=rating_system.ace_pot_manager.get_balance(),
                                      ace_pot_config=rating_system.ace_pot_manager.get_config())
    
    # Get all players with their ratings
    players = []
    for name, data in rating_system.players.items():
        players.append({
            'name': name,
            'rating': data['rating'],
            'is_club_member': data.get('is_club_member', False)
        })
    
    # Sort by name
    players.sort(key=lambda x: x['name'])
    
    return render_template('event_registration.html', 
                          players=players,
                          ace_pot=rating_system.ace_pot_manager.get_balance(),
                          ace_pot_config=rating_system.ace_pot_manager.get_config())

@app.route('/record_tournament', methods=['GET', 'POST'])
@login_required
def record_tournament():
    """Record a new tournament."""
    if request.method == 'POST':
        course = request.form.get('course')
        date = request.form.get('date')
        
        if not date:
            date = datetime.datetime.now().strftime("%Y-%m-%d")
        
        # Get all valid player names for validation
        valid_players = list(rating_system.players.keys())
        
        # Process team results
        team_results = []
        for i in range(20):  # Support up to 20 teams
            player1 = request.form.get(f'player1_{i}')
            player2 = request.form.get(f'player2_{i}')
            score = request.form.get(f'score_{i}')
            
            # Skip empty rows
            if not (player1 and player2 and score):
                continue
                
            # Validate player names
            if player1 != "Ghost Player" and not any(p.lower() == player1.lower() for p in valid_players):
                flash(f"Invalid player name: {player1}", "error")
                return render_template('record_tournament.html', 
                                      players=valid_players,
                                      now_date=datetime.datetime.now().strftime("%Y-%m-%d"),
                                      ace_pot=rating_system.ace_pot_manager.get_balance())
                
            if player2 != "Ghost Player" and not any(p.lower() == player2.lower() for p in valid_players):
                flash(f"Invalid player name: {player2}", "error")
                return render_template('record_tournament.html', 
                                      players=valid_players,
                                      now_date=datetime.datetime.now().strftime("%Y-%m-%d"),
                                      ace_pot=rating_system.ace_pot_manager.get_balance())
                
            try:
                score = int(score)
                team_results.append(((player1, player2), score))
            except ValueError:
                flash(f"Invalid score for team {player1} & {player2}", "error")
                return render_template('record_tournament.html', 
                                      players=valid_players,
                                      now_date=datetime.datetime.now().strftime("%Y-%m-%d"),
                                      ace_pot=rating_system.ace_pot_manager.get_balance())
        
        # Check if we have at least 2 teams
        if len(team_results) < 2:
            flash("At least 2 teams are required to record a tournament", "error")
            return render_template('record_tournament.html', 
                                  players=valid_players,
                                  now_date=datetime.datetime.now().strftime("%Y-%m-%d"),
                                  ace_pot=rating_system.ace_pot_manager.get_balance())
        
        # Process ace pot
        ace_pot_paid = request.form.get('ace_pot_paid') == 'on'
        
        # Get all ace pot recipients
        ace_pot_recipients = []
        for i in range(20):  # Support up to 20 recipients
            recipient = request.form.get(f'ace_pot_recipient_{i}')
            if recipient and recipient in valid_players:
                ace_pot_recipients.append(recipient)
        
        try:
            # Record the tournament
            tournament_id = rating_system.record_tournament(team_results, course, date, ace_pot_paid)
            
            # Process ace pot payouts if needed
            if ace_pot_paid and ace_pot_recipients:
                for recipient in ace_pot_recipients:
                    rating_system.ace_pot_manager.process_payout(tournament_id, recipient)
                
                if len(ace_pot_recipients) == 1:
                    flash(f"Ace pot paid to {ace_pot_recipients[0]}", "success")
                else:
                    flash(f"Ace pot paid to {', '.join(ace_pot_recipients)}", "success")
            
            # Process ace pot buy-ins from the event registration
            ace_pot_buy_ins = session.get('ace_pot_buy_ins', [])
            if ace_pot_buy_ins:
                print(f"Processing batch ace pot buy-ins for {len(ace_pot_buy_ins)} players")
                result = rating_system.ace_pot_manager.process_batch_buy_ins(tournament_id, ace_pot_buy_ins)
                
                # Clear the session data
                session.pop('ace_pot_buy_ins', None)
                
                if result['success'] > 0:
                    flash(f"Added ${result['amount']:.2f} to ace pot from {result['success']} players", "success")
                if result['failure'] > 0:
                    flash(f"Failed to process ace pot buy-in for {result['failure']} players", "warning")
            
            flash(f"Tournament recorded with {len(team_results)} teams", "success")
            return redirect(url_for('list_tournaments'))
        except Exception as e:
            import traceback
            print(f"Error recording tournament: {str(e)}")
            print(traceback.format_exc())
            flash(f"Error recording tournament: {str(e)}", "error")
            return render_template('record_tournament.html', 
                                  players=valid_players,
                                  now_date=datetime.datetime.now().strftime("%Y-%m-%d"),
                                  ace_pot=rating_system.ace_pot_manager.get_balance())
    
    # Check if teams were passed from the generate_teams page
    teams_data = request.args.get('teams')
    pre_populated_teams = []
    
    if teams_data:
        import json
        try:
            # Parse the JSON string back into a list
            pre_populated_teams = json.loads(teams_data)
            print(f"Successfully loaded pre-populated teams: {pre_populated_teams}")
        except json.JSONDecodeError as e:
            print(f"Error parsing teams data: {e}")
            print(f"Raw teams data: {teams_data}")
            flash("Error loading team data", "error")
    
    return render_template('record_tournament.html', 
                          players=list(rating_system.players.keys()),
                          now_date=datetime.datetime.now().strftime("%Y-%m-%d"),
                          pre_populated_teams=pre_populated_teams,
                          ace_pot=rating_system.ace_pot_manager.get_balance())

@app.route('/tournaments')
def list_tournaments():
    """List all tournaments."""
    tournaments = rating_system.tournaments
    
    # Sort by date (newest first)
    tournaments.sort(key=lambda x: x['date'], reverse=True)
    
    return render_template('tournaments.html', tournaments=tournaments)

@app.route('/storage', methods=['GET', 'POST'])
def storage_settings():
    """Change storage settings."""
    if request.method == 'POST':
        storage_type = request.form.get('storage_type')
        
        if storage_type == 'db':
            # Switch to database storage
            if not rating_system.use_db:
                rating_system.switch_to_db()
                flash("Switched to database storage", "success")
        elif storage_type == 'json':
            # Switch to JSON storage
            if rating_system.use_db:
                rating_system.switch_to_json()
                flash("Switched to JSON storage", "success")
        else:
            flash("Invalid storage type", "error")
            
        return redirect(url_for('storage_settings'))
    
    return render_template('storage_settings.html', 
                          use_db=rating_system.use_db,
                          db_file=rating_system.db_file,
                          json_file=rating_system.json_file)

# Ace Pot Routes
@app.route('/ace_pot')
def ace_pot():
    """Ace pot tracker page."""
    ace_pot_balance = rating_system.ace_pot_manager.get_balance()
    ace_pot_config = rating_system.ace_pot_manager.get_config()
    ace_pot_ledger = rating_system.ace_pot_manager.get_ledger()
    
    return render_template('ace_pot.html',
                          ace_pot=ace_pot_balance,
                          ace_pot_config=ace_pot_config,
                          ledger=ace_pot_ledger)

@app.route('/update_ace_pot_config', methods=['POST'])
@login_required
def update_ace_pot_config():
    """Update ace pot configuration."""
    cap_amount = request.form.get('cap_amount')
    
    try:
        cap_amount = float(cap_amount)
        if cap_amount < 0:
            flash("Cap amount must be a positive number", "error")
            return redirect(url_for('ace_pot'))
            
        rating_system.ace_pot_manager.update_config(cap_amount)
        flash(f"Ace pot cap updated to ${cap_amount}", "success")
    except ValueError:
        flash("Invalid cap amount", "error")
    
    return redirect(url_for('ace_pot'))

@app.route('/set_ace_pot_balance', methods=['POST'])
@login_required
def set_ace_pot_balance():
    """Set ace pot balance."""
    new_balance = request.form.get('new_balance')
    description = request.form.get('description')
    
    try:
        new_balance = float(new_balance)
        if new_balance < 0:
            flash("Balance must be a positive number", "error")
            return redirect(url_for('ace_pot'))
            
        rating_system.ace_pot_manager.set_balance(new_balance, description)
        flash(f"Ace pot balance updated to ${new_balance}", "success")
    except ValueError:
        flash("Invalid balance amount", "error")
    
    return redirect(url_for('ace_pot'))

if __name__ == '__main__':
    app.run(debug=True)
