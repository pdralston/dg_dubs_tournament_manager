#!/usr/bin/env python3
"""
Migrate dg_dubs data from SQLite to MySQL (RDS).

Usage:
    python migrate_sqlite_to_mysql.py

Requires:
    pip install pymysql python-dotenv
"""

import sqlite3
import pymysql
import os
import sys
from dotenv import load_dotenv

load_dotenv()

SQLITE_FILE = os.path.join(os.path.dirname(__file__), '..', 'web_app', 'tournament_data.db')

MYSQL_HOST = os.getenv('DB_HOST')
MYSQL_PORT = int(os.getenv('DB_PORT', 3306))
MYSQL_USER = os.getenv('DB_USER')
MYSQL_PASSWORD = os.getenv('DB_PASSWORD')
MYSQL_DB = os.getenv('DB_NAME', 'dg_dubs')


def get_sqlite_conn():
    conn = sqlite3.connect(SQLITE_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def get_mysql_conn():
    return pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DB,
        cursorclass=pymysql.cursors.DictCursor
    )


def migrate():
    print(f"Reading from SQLite: {SQLITE_FILE}")
    sqlite = get_sqlite_conn()
    mysql = get_mysql_conn()

    try:
        sc = sqlite.cursor()
        mc = mysql.cursor()

        # --- Players ---
        print("Migrating players...")
        sc.execute("SELECT * FROM players ORDER BY id")
        players = sc.fetchall()
        player_id_map = {}  # old sqlite id -> new mysql id

        for p in players:
            mc.execute(
                "INSERT INTO players (name, rating, tournaments_played) VALUES (%s, %s, %s)",
                (p['name'], p['rating'], p['tournaments_played'])
            )
            player_id_map[p['id']] = mc.lastrowid

        mysql.commit()
        print(f"  {len(players)} players migrated.")

        # --- Tournaments ---
        print("Migrating tournaments...")
        sc.execute("SELECT * FROM tournaments ORDER BY id")
        tournaments = sc.fetchall()
        tournament_id_map = {}

        for t in tournaments:
            t = dict(t)
            ace_pot_paid_to = player_id_map.get(t.get('ace_pot_paid_to')) if t.get('ace_pot_paid_to') else None
            mc.execute(
                """INSERT INTO tournaments (date, course, team_count, ace_pot_paid, ace_pot_paid_to)
                   VALUES (%s, %s, %s, %s, %s)""",
                (t['date'], t.get('course'), t['team_count'],
                 bool(t.get('ace_pot_paid', 0)), ace_pot_paid_to)
            )
            tournament_id_map[t['id']] = mc.lastrowid

        mysql.commit()
        print(f"  {len(tournaments)} tournaments migrated.")

        # --- Teams ---
        print("Migrating teams...")
        sc.execute("SELECT * FROM teams ORDER BY id")
        teams = sc.fetchall()

        for t in teams:
            p1 = player_id_map.get(t['player1_id'])
            p2 = player_id_map.get(t['player2_id']) if t['player2_id'] and t['player2_id'] != -1 else None
            tid = tournament_id_map.get(t['tournament_id'])
            if not tid or not p1:
                print(f"  Skipping team id={t['id']}: missing tournament or player1")
                continue
            mc.execute(
                """INSERT INTO teams
                   (tournament_id, player1_id, player2_id, is_ghost_team, position,
                    expected_position, score, team_rating)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                (tid, p1, p2, p2 is None,
                 t['position'], t['expected_position'], t['score'], t['team_rating'])
            )

        mysql.commit()
        print(f"  {len(teams)} teams migrated.")

        # --- Player history ---
        print("Migrating player history...")
        sc.execute("SELECT * FROM player_history ORDER BY id")
        history = sc.fetchall()

        for h in history:
            pid = player_id_map.get(h['player_id'])
            tid = tournament_id_map.get(h['tournament_id'])
            if not pid or not tid:
                continue
            mc.execute(
                """INSERT INTO player_history
                   (player_id, tournament_id, old_rating, new_rating, position,
                    expected_position, score, with_ghost)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                (pid, tid, h['old_rating'], h['new_rating'], h['position'],
                 h['expected_position'], h['score'], bool(h['with_ghost']))
            )

        mysql.commit()
        print(f"  {len(history)} history entries migrated.")

        # --- Tournament participants ---
        print("Migrating tournament participants...")
        sc.execute("SELECT * FROM tournament_participants ORDER BY id")
        participants = sc.fetchall()

        for p in participants:
            pid = player_id_map.get(p['player_id'])
            tid = tournament_id_map.get(p['tournament_id'])
            if not pid or not tid:
                continue
            mc.execute(
                """INSERT INTO tournament_participants (tournament_id, player_id, ace_pot_buy_in)
                   VALUES (%s, %s, %s)""",
                (tid, pid, bool(p['ace_pot_buy_in']))
            )

        mysql.commit()
        print(f"  {len(participants)} participants migrated.")

        # --- Ace pot tracker ---
        print("Migrating ace pot ledger...")
        sc.execute("SELECT * FROM ace_pot_tracker ORDER BY id")
        entries = sc.fetchall()

        for e in entries:
            tid = tournament_id_map.get(e['tournament_id']) if e['tournament_id'] else None
            pid = player_id_map.get(e['player_id']) if e['player_id'] else None
            mc.execute(
                """INSERT INTO ace_pot_tracker (date, description, amount, balance, tournament_id, player_id)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (e['date'], e['description'], e['amount'], e['balance'], tid, pid)
            )

        mysql.commit()
        print(f"  {len(entries)} ace pot entries migrated.")

        # --- Ace pot config ---
        print("Migrating ace pot config...")
        sc.execute("SELECT cap_amount FROM ace_pot_config WHERE id = 1")
        config = sc.fetchone()
        if config:
            mc.execute(
                "UPDATE ace_pot_config SET cap_amount = %s WHERE id = 1",
                (config['cap_amount'],)
            )
            mysql.commit()
            print(f"  cap_amount set to {config['cap_amount']}")

        print("\nMigration complete.")

    except Exception as e:
        mysql.rollback()
        print(f"Migration failed: {e}")
        raise
    finally:
        sqlite.close()
        mysql.close()


if __name__ == '__main__':
    if not all([MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD]):
        print("Error: DB_HOST, DB_USER, and DB_PASSWORD must be set in environment or .env file")
        sys.exit(1)
    migrate()
