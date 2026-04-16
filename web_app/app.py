#!/usr/bin/env python3
"""
Disc Golf League Tournament Rating System - Web Application

Flask web interface backed by MySQL via SQLAlchemy.
"""

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, g
from dotenv import load_dotenv
import os
import sys
import datetime
import json

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tournament_core.models import db, User
from tournament_core import TournamentRatingSystem
from web_app.auth import AuthManager, login_required, is_authenticated, get_current_user
from web_app.api import all_blueprints

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev_key_for_testing_change_in_production')

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

# Initialize within app context
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
        count = User.query.filter_by(role='admin').count()
        if count == 0:
            success, msg = auth_manager.create_user(admin_user, admin_pass, 'admin')
            if success:
                print(f"Admin user '{admin_user}' created successfully")

# Register API blueprints
for blueprint in all_blueprints:
    app.register_blueprint(blueprint)


@app.context_processor
def inject_user():
    return dict(current_user=get_current_user())


# ── Auth routes ──────────────────────────────────────────────────────

@app.route('/login', methods=['GET', 'POST'])
def login():
    if is_authenticated():
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        if not username or not password:
            flash('Please enter both username and password.', 'error')
            return render_template('auth/login.html')
        ip_address = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
        success, result = auth_manager.authenticate_user(username, password, ip_address)
        if success:
            session['session_token'] = result['session_token']
            session['user_id'] = result['user_id']
            session['username'] = result['username']
            session['role'] = result['role']
            flash(f'Welcome back, {result["username"]}!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        flash(result, 'error')
    return render_template('auth/login.html')


@app.route('/logout')
def logout():
    if 'session_token' in session:
        auth_manager.logout_user(session['session_token'])
    session.clear()
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('index'))


@app.route('/register', methods=['GET', 'POST'])
@login_required
def register():
    current_user = get_current_user()
    if not current_user or current_user['role'] != 'admin':
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        role = request.form.get('role', 'organizer')
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
        success, message = auth_manager.create_user(username, password, role)
        if success:
            flash(f'User "{username}" created successfully with role "{role}".', 'success')
            return redirect(url_for('register'))
        flash(message, 'error')
    return render_template('auth/register.html')


@app.route('/profile')
@login_required
def profile():
    return render_template('auth/profile.html', user=get_current_user())


# ── Main routes ──────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/players')
def list_players():
    players = []
    for name, data in rating_system.players.items():
        players.append({
            'name': name,
            'rating': data['rating'],
            'tournaments_played': data['tournaments_played'],
        })
    players.sort(key=lambda x: x['rating'], reverse=True)
    return render_template('players.html', players=players)


@app.route('/player/<name>')
def player_details(name):
    try:
        player_data = rating_system.get_player(name)
        history = sorted(player_data.get('history', []), key=lambda x: x['tournament_date'], reverse=True)
        return render_template('player_details.html',
                               name=name, rating=player_data['rating'],
                               tournaments_played=player_data['tournaments_played'],
                               history=history)
    except ValueError:
        flash(f"Player {name} not found", "error")
        return redirect(url_for('list_players'))


@app.route('/add_player', methods=['GET', 'POST'])
@login_required
def add_player():
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
    return redirect(url_for('event_registration'))


@app.route('/event_registration', methods=['GET', 'POST'])
@login_required
def event_registration():
    if request.method == 'POST':
        selected_players = request.form.getlist('players')
        allow_ghost = 'allow_ghost' in request.form

        if len(selected_players) < 2:
            flash("Select at least 2 players", "error")
            return render_template('event_registration.html',
                                   players=list(rating_system.players.keys()),
                                   ace_pot=rating_system.ace_pot_manager.get_balance())

        # Process new players
        new_players_added = []
        for player_name in selected_players:
            if request.form.get(f'is_new_player_{player_name}') == 'true':
                rating = float(request.form.get(f'rating_{player_name}', 1000))
                is_club_member = request.form.get(f'club_member_{player_name}') == 'on'
                try:
                    if not rating_system.player_exists(player_name):
                        rating_system.add_player(player_name, rating, is_club_member)
                        new_players_added.append(player_name)
                except ValueError as e:
                    flash(str(e), "error")
                    return render_template('event_registration.html',
                                           players=list(rating_system.players.keys()),
                                           ace_pot=rating_system.ace_pot_manager.get_balance(),
                                           ace_pot_config=rating_system.ace_pot_manager.get_config())

        if new_players_added:
            rating_system._load_from_db()

        # Update club membership for existing players
        for player_name in selected_players:
            if request.form.get(f'is_new_player_{player_name}') != 'true':
                is_club_member = request.form.get(f'club_member_{player_name}') == 'on'
                try:
                    rating_system.update_player_club_membership(player_name, is_club_member)
                except Exception as e:
                    print(f"Error updating club membership for {player_name}: {e}")

            # Ace pot buy-ins
            ace_pot_buy_ins = [p for p in selected_players if request.form.get(f'ace_pot_{p}') == 'on']
            if ace_pot_buy_ins:
                session['ace_pot_buy_ins'] = ace_pot_buy_ins

            try:
                teams = rating_system.generate_balanced_teams(selected_players, allow_ghost=True)
                predictions = rating_system.predict_tournament_outcome([tuple(t) for t in teams])
                team_data = [{
                    'players': team,
                    'rating': rating_system.calculate_team_rating(team[0], team[1]),
                    'expected_position': predictions[tuple(team)].get('expected_position', 0),
                } for team in teams]
                return render_template('team_results.html', teams=team_data)
            except ValueError as e:
                flash(str(e), "error")
                return render_template('event_registration.html',
                                       players=list(rating_system.players.keys()),
                                       ace_pot=rating_system.ace_pot_manager.get_balance(),
                                       ace_pot_config=rating_system.ace_pot_manager.get_config())

    players = [{'name': n, 'rating': d['rating'], 'is_club_member': d.get('is_club_member', False)}
               for n, d in rating_system.players.items()]
    players.sort(key=lambda x: x['name'])
    return render_template('event_registration.html',
                           players=players,
                           ace_pot=rating_system.ace_pot_manager.get_balance(),
                           ace_pot_config=rating_system.ace_pot_manager.get_config())


@app.route('/record_tournament', methods=['GET', 'POST'])
@login_required
def record_tournament():
    valid_players = list(rating_system.players.keys())

    if request.method == 'POST':
        course = request.form.get('course')
        date = request.form.get('date') or datetime.datetime.now().strftime("%Y-%m-%d")

        team_results = []
        for i in range(20):
            p1 = request.form.get(f'player1_{i}')
            p2 = request.form.get(f'player2_{i}')
            score = request.form.get(f'score_{i}')
            if not (p1 and p2 and score):
                continue
            for p in [p1, p2]:
                if p != "Ghost Player" and not any(v.lower() == p.lower() for v in valid_players):
                    flash(f"Invalid player name: {p}", "error")
                    return render_template('record_tournament.html', players=valid_players,
                                           now_date=datetime.datetime.now().strftime("%Y-%m-%d"),
                                           ace_pot=rating_system.ace_pot_manager.get_balance())
            try:
                team_results.append(((p1, p2), int(score)))
            except ValueError:
                flash(f"Invalid score for team {p1} & {p2}", "error")
                return render_template('record_tournament.html', players=valid_players,
                                       now_date=datetime.datetime.now().strftime("%Y-%m-%d"),
                                       ace_pot=rating_system.ace_pot_manager.get_balance())

        if len(team_results) < 2:
            flash("At least 2 teams are required to record a tournament", "error")
            return render_template('record_tournament.html', players=valid_players,
                                   now_date=datetime.datetime.now().strftime("%Y-%m-%d"),
                                   ace_pot=rating_system.ace_pot_manager.get_balance())

        ace_pot_paid = request.form.get('ace_pot_paid') == 'on'
        ace_pot_recipients = [request.form.get(f'ace_pot_recipient_{i}')
                              for i in range(20)
                              if request.form.get(f'ace_pot_recipient_{i}') in valid_players]

        try:
            tournament_id = rating_system.record_tournament(team_results, course, date, ace_pot_paid)

            if ace_pot_paid and ace_pot_recipients:
                for r in ace_pot_recipients:
                    rating_system.ace_pot_manager.process_payout(tournament_id, r)
                flash(f"Ace pot paid to {', '.join(ace_pot_recipients)}", "success")

            ace_pot_buy_ins = session.get('ace_pot_buy_ins', [])
            if ace_pot_buy_ins:
                result = rating_system.ace_pot_manager.process_batch_buy_ins(tournament_id, ace_pot_buy_ins)
                session.pop('ace_pot_buy_ins', None)
                if result['success'] > 0:
                    flash(f"Added ${result['amount']:.2f} to ace pot from {result['success']} players", "success")

            flash(f"Tournament recorded with {len(team_results)} teams", "success")
            return redirect(url_for('list_tournaments'))
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            flash(f"Error recording tournament: {e}", "error")
            return render_template('record_tournament.html', players=valid_players,
                                   now_date=datetime.datetime.now().strftime("%Y-%m-%d"),
                                   ace_pot=rating_system.ace_pot_manager.get_balance())

    teams_data = request.args.get('teams')
    pre_populated_teams = []
    if teams_data:
        try:
            pre_populated_teams = json.loads(teams_data)
        except json.JSONDecodeError:
            flash("Error loading team data", "error")

    return render_template('record_tournament.html', players=valid_players,
                           now_date=datetime.datetime.now().strftime("%Y-%m-%d"),
                           pre_populated_teams=pre_populated_teams,
                           ace_pot=rating_system.ace_pot_manager.get_balance())


@app.route('/tournaments')
def list_tournaments():
    tournaments = sorted(rating_system.tournaments, key=lambda x: x['date'], reverse=True)
    return render_template('tournaments.html', tournaments=tournaments)


@app.route('/ace_pot')
def ace_pot():
    return render_template('ace_pot.html',
                           ace_pot=rating_system.ace_pot_manager.get_balance(),
                           ace_pot_config=rating_system.ace_pot_manager.get_config(),
                           ledger=rating_system.ace_pot_manager.get_ledger())


@app.route('/update_ace_pot_config', methods=['POST'])
@login_required
def update_ace_pot_config():
    try:
        cap_amount = float(request.form.get('cap_amount'))
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
    try:
        new_balance = float(request.form.get('new_balance'))
        if new_balance < 0:
            flash("Balance must be a positive number", "error")
            return redirect(url_for('ace_pot'))
        description = request.form.get('description')
        rating_system.ace_pot_manager.set_balance(new_balance, description)
        flash(f"Ace pot balance updated to ${new_balance}", "success")
    except ValueError:
        flash("Invalid balance amount", "error")
    return redirect(url_for('ace_pot'))


if __name__ == '__main__':
    app.run(debug=True)
