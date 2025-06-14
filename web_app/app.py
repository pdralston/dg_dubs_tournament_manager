#!/usr/bin/env python3
"""
Disc Golf League Tournament Rating System - Web Application

This module provides a web interface for the tournament rating system.
"""

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import os
import datetime
import sys

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from tournament_core import TournamentRatingSystem

# Import API blueprints
from api import all_blueprints

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev_key_for_testing')

# Register API blueprints
for blueprint in all_blueprints:
    app.register_blueprint(blueprint)

# Initialize the rating system
rating_system = TournamentRatingSystem()

@app.template_filter('player_rating')
def player_rating(player_name):
    """Get a player's rating."""
    try:
        return rating_system.get_player(player_name)['rating']
    except (ValueError, KeyError):
        return 0

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
def event_registration():
    """Event registration and team generation."""
    if request.method == 'POST':
        selected_players = request.form.getlist('players')
        allow_ghost = 'allow_ghost' in request.form
        
        if len(selected_players) < 2:
            flash("Select at least 2 players", "error")
            return render_template('event_registration.html', 
                                  players=list(rating_system.players.keys()),
                                  ace_pot=rating_system.ace_pot_manager.get_balance(),
                                  ace_pot_config=rating_system.ace_pot_manager.get_config())
        
        # Process new players
        for player_name in selected_players:
            is_new_player = request.form.get(f'is_new_player_{player_name}') == 'true'
            if is_new_player:
                rating = float(request.form.get(f'rating_{player_name}', 1000))
                is_club_member = request.form.get(f'club_member_{player_name}') == 'on'
                
                try:
                    rating_system.add_player(player_name, rating, is_club_member)
                except ValueError as e:
                    flash(str(e), "error")
                    return render_template('event_registration.html', 
                                          players=list(rating_system.players.keys()),
                                          ace_pot=rating_system.ace_pot_manager.get_balance(),
                                          ace_pot_config=rating_system.ace_pot_manager.get_config())
            else:
                # Update existing player club membership
                is_club_member = request.form.get(f'club_member_{player_name}') == 'on'
                rating_system.update_player_club_membership(player_name, is_club_member)
            
            # Process ace pot buy-ins
            ace_pot_buy_in = request.form.get(f'ace_pot_{player_name}') == 'on'
            if ace_pot_buy_in:
                # This will be handled when recording the tournament
                pass
        
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
            if player1 != "Ghost Player" and player1 not in valid_players:
                flash(f"Invalid player name: {player1}", "error")
                return render_template('record_tournament.html', 
                                      players=valid_players,
                                      now_date=datetime.datetime.now().strftime("%Y-%m-%d"),
                                      ace_pot=rating_system.ace_pot_manager.get_balance())
                
            if player2 != "Ghost Player" and player2 not in valid_players:
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
            
            flash(f"Tournament recorded with {len(team_results)} teams", "success")
            return redirect(url_for('list_tournaments'))
        except ValueError as e:
            flash(str(e), "error")
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
        except json.JSONDecodeError:
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
