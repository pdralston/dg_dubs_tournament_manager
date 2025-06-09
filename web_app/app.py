#!/usr/bin/env python3
"""
Disc Golf League Tournament Rating System - Web Application

This module provides a web interface for the tournament rating system.
"""

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from tournament_core import TournamentRatingSystem
import os
import datetime

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev_key_for_testing')

# Initialize the rating system
rating_system = TournamentRatingSystem()

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
    
    # Sort by rating (descending)
    players.sort(key=lambda x: x['rating'], reverse=True)
    
    return render_template('players.html', players=players)

@app.route('/player/<name>')
def player_details(name):
    """Show details for a specific player."""
    try:
        player_name = rating_system.get_player_name(name)  # Handle case-insensitive lookup
        player_data = rating_system.get_player(player_name)
        
        # Format history for display
        history = []
        for entry in player_data.get('history', []):
            history.append({
                'date': entry['tournament_date'],
                'position': entry['position'],
                'expected_position': entry['expected_position'],
                'old_rating': entry['old_rating'],
                'new_rating': entry['new_rating'],
                'change': entry['change'],
                'with_ghost': entry['with_ghost']
            })
        
        return render_template('player_details.html', 
                              name=player_name, 
                              rating=player_data['rating'],
                              tournaments_played=player_data['tournaments_played'],
                              history=history)
    except ValueError:
        flash(f"Player '{name}' not found", "error")
        return redirect(url_for('list_players'))

@app.route('/tournaments')
def list_tournaments():
    """List all tournaments."""
    tournaments = []
    for tournament in rating_system.tournaments:
        tournaments.append({
            'date': tournament['date'],
            'course': tournament['course'],
            'teams': tournament['teams'],
            'results': tournament['results']
        })
    
    # Sort by date (most recent first)
    tournaments.sort(key=lambda x: x['date'], reverse=True)
    
    return render_template('tournaments.html', tournaments=tournaments)

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

@app.route('/record_tournament', methods=['GET', 'POST'])
def record_tournament():
    """Record a new tournament."""
    if request.method == 'POST':
        course = request.form.get('course')
        date = request.form.get('date')
        
        if not date:
            date = datetime.datetime.now().strftime("%Y-%m-%d")
        
        # Process team results
        team_results = []
        for i in range(10):  # Support up to 10 teams
            player1 = request.form.get(f'player1_{i}')
            player2 = request.form.get(f'player2_{i}')
            score = request.form.get(f'score_{i}')
            
            if player1 and player2 and score:
                try:
                    score = int(score)
                    team_results.append(((player1, player2), score))
                except ValueError:
                    flash(f"Invalid score for team {player1} & {player2}", "error")
                    return render_template('record_tournament.html', 
                                          players=list(rating_system.players.keys()))
        
        if not team_results:
            flash("No valid team results provided", "error")
            return render_template('record_tournament.html', 
                                  players=list(rating_system.players.keys()))
        
        try:
            rating_system.record_tournament(team_results, course, date)
            flash(f"Tournament recorded with {len(team_results)} teams", "success")
            return redirect(url_for('list_tournaments'))
        except ValueError as e:
            flash(str(e), "error")
            return render_template('record_tournament.html', 
                                  players=list(rating_system.players.keys()))
    
    return render_template('record_tournament.html', 
                          players=list(rating_system.players.keys()),
                          now_date=datetime.datetime.now().strftime("%Y-%m-%d"))

@app.route('/generate_teams', methods=['GET', 'POST'])
def generate_teams():
    """Generate balanced teams."""
    if request.method == 'POST':
        selected_players = request.form.getlist('players')
        allow_ghost = 'allow_ghost' in request.form
        
        if len(selected_players) < 2:
            flash("Select at least 2 players", "error")
            return render_template('generate_teams.html', 
                                  players=list(rating_system.players.keys()))
        
        try:
            teams = rating_system.generate_balanced_teams(selected_players, allow_ghost)
            predictions = rating_system.predict_tournament_outcome([tuple(team) for team in teams])
            
            # Format for template
            team_data = []
            for i, team in enumerate(teams):
                team_data.append({
                    'players': team,
                    'rating': rating_system.calculate_team_rating(team[0], team[1]),
                    'expected_position': predictions[tuple(team)]['expected_position']
                })
            
            return render_template('team_results.html', teams=team_data)
        except ValueError as e:
            flash(str(e), "error")
            return render_template('generate_teams.html', 
                                  players=list(rating_system.players.keys()))
    
    return render_template('generate_teams.html', 
                          players=list(rating_system.players.keys()))

@app.route('/api/players')
def api_players():
    """API endpoint for players."""
    players = {}
    for name, data in rating_system.players.items():
        players[name] = {
            'rating': data['rating'],
            'tournaments_played': data['tournaments_played']
        }
    return jsonify(players)

@app.route('/api/tournaments')
def api_tournaments():
    """API endpoint for tournaments."""
    return jsonify(rating_system.tournaments)

@app.route('/storage', methods=['GET', 'POST'])
def storage_settings():
    """Change storage settings."""
    if request.method == 'POST':
        storage_type = request.form.get('storage_type')
        
        if storage_type == 'db':
            rating_system.switch_storage_mode(True)
            flash("Switched to database storage", "success")
        elif storage_type == 'json':
            rating_system.switch_storage_mode(False)
            flash("Switched to JSON storage", "success")
        
        return redirect(url_for('index'))
    
    return render_template('storage.html', 
                          current_storage='Database' if rating_system.use_db else 'JSON')

if __name__ == '__main__':
    app.run(debug=True)
