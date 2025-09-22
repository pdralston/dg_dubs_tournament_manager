import os
import sqlite3
import subprocess

def restore_from_backup():
    """Restore database from SQL backup if no database exists"""
    if not os.path.exists('tournament_data.db') and os.path.exists('data_backup.sql'):
        try:
            subprocess.run(['sqlite3', 'tournament_data.db', '.read data_backup.sql'], check=True)
            print("Database restored from backup")
        except subprocess.CalledProcessError:
            print("Failed to restore database from backup")

def replace_database_from_file(db_file_path):
    """Replace current database with specified file"""
    if os.path.exists(db_file_path):
        if os.path.exists('tournament_data.db'):
            os.remove('tournament_data.db')
        os.rename(db_file_path, 'tournament_data.db')
        print(f"Database replaced with {db_file_path}")
    else:
        print(f"File {db_file_path} not found")
