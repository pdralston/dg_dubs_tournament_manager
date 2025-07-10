#!/usr/bin/env python3
"""
Create initial admin user for the Disc Golf League Tournament Rating System.
"""

import sys
import os
import getpass

# Add the web_app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'web_app'))

from auth import AuthManager

def create_admin_user():
    """Create an initial admin user."""
    print("Creating initial admin user for Disc Golf League Tournament Rating System")
    print("=" * 60)
    
    # Initialize auth manager
    db_file = os.path.join(os.path.dirname(__file__), 'web_app', 'tournament_data.db')
    auth_manager = AuthManager(db_file)
    
    # Get username
    while True:
        username = input("Enter admin username (min 3 characters): ").strip()
        if len(username) >= 3:
            break
        print("Username must be at least 3 characters long.")
    
    # Get password
    while True:
        password = getpass.getpass("Enter admin password (min 8 characters): ")
        if len(password) >= 8:
            confirm_password = getpass.getpass("Confirm admin password: ")
            if password == confirm_password:
                break
            else:
                print("Passwords do not match. Please try again.")
        else:
            print("Password must be at least 8 characters long.")
    
    # Create the user
    success, message = auth_manager.create_user(username, password, 'admin')
    
    if success:
        print(f"\n✅ Admin user '{username}' created successfully!")
        print("\nYou can now:")
        print("1. Start the web application: cd web_app && python app.py")
        print("2. Login at: http://localhost:5000/login")
        print("3. Create additional organizer accounts from the admin panel")
    else:
        print(f"\n❌ Error creating admin user: {message}")
        return False
    
    return True

if __name__ == "__main__":
    try:
        create_admin_user()
    except KeyboardInterrupt:
        print("\n\nOperation cancelled.")
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)
