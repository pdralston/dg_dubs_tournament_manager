#!/usr/bin/env python3
"""
Test script for the web application API endpoints.
"""

from app import app
from flask import json

def test_players_api():
    """Test the players API endpoint."""
    with app.test_client() as client:
        response = client.get('/api/players')
        print(f'Status code: {response.status_code}')
        if response.status_code == 200:
            data = json.loads(response.data)
            print(f'Number of players: {len(data)}')
            print('First few players:')
            for player in data[:3]:
                print(f"  {player['name']}: {player['rating']}")
        else:
            print(f'Error: {response.data}')

def test_tournaments_api():
    """Test the tournaments API endpoint."""
    with app.test_client() as client:
        response = client.get('/api/tournaments')
        print(f'Status code: {response.status_code}')
        if response.status_code == 200:
            data = json.loads(response.data)
            print(f'Number of tournaments: {len(data)}')
            if data:
                print(f"First tournament: {data[0]['date']} at {data[0]['course']}")
        else:
            print(f'Error: {response.data}')

def test_storage_api():
    """Test the storage API endpoint."""
    with app.test_client() as client:
        response = client.get('/api/storage')
        print(f'Status code: {response.status_code}')
        if response.status_code == 200:
            data = json.loads(response.data)
            print(f"Storage mode: {data.get('mode')}")
            print(f"Storage file: {data.get('file')}")
        else:
            print(f'Error: {response.data}')

if __name__ == '__main__':
    print("\nTesting Players API:")
    test_players_api()
    
    print("\nTesting Tournaments API:")
    test_tournaments_api()
    
    print("\nTesting Storage API:")
    test_storage_api()
