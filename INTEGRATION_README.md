# Disc Golf League Tournament Rating System - Integration Solution

## Overview
This document outlines the architecture for integrating the disc golf league tournament rating system with a Wix website, using a two-tier access approach that separates public-facing features from administrative functionality.

## Architecture

### Two-Tier Access Model
1. **Public Tier (Wix Integration)**
   - Read-only access to tournament results and player statistics
   - Embedded within Wix website for seamless user experience
   - Available to all league players and visitors

2. **Administrative Tier (Separate Web Application)**
   - Full edit functionality for tournament directors
   - Hosted separately with proper authentication
   - Includes all management features (adding players, recording tournaments, etc.)

## Implementation Components

### Backend API
- REST API with role-based access control
- Serves both public and administrative tiers
- Public endpoints require no authentication
- Administrative endpoints require authentication with appropriate permissions
- Built with Python (Flask/FastAPI) leveraging existing tournament rating system

### Wix Integration (Public Tier)
- Uses Wix Velo to make API calls to read-only endpoints
- Custom pages for:
  - Player leaderboards and statistics
  - Tournament results and history
  - Team performance analytics
  - Upcoming tournament information

### Administrative Portal
- Dedicated web application with full CRUD functionality
- Secure login for tournament directors
- All management features from the current system
- Hosted on a reliable platform (Heroku, Render, AWS, etc.)

## Benefits
- **Security**: Administrative functions are properly protected
- **Simplicity**: Public users get a clean, focused interface
- **Integration**: Maintains the look and feel of your Wix site for public users
- **Flexibility**: Tournament directors have access to all features without Wix limitations
- **Performance**: Separating concerns allows each interface to be optimized for its purpose

## Technical Implementation Notes

### API Endpoints Example
```python
# Public endpoints - no authentication required
@app.route('/api/players', methods=['GET'])
def get_players():
    players = rating_system.get_player_ratings()
    return jsonify(players)

# Admin endpoint - requires authentication
@app.route('/api/tournaments', methods=['POST'])
@jwt_required()
def add_tournament():
    # Verify user is an admin
    current_user = get_jwt_identity()
    if current_user['role'] != 'admin':
        return jsonify({"msg": "Unauthorized"}), 403
        
    # Process the tournament data
    data = request.json
    # ... implementation details ...
    return jsonify({"msg": "Tournament added successfully"})
```

## Next Steps
1. Develop the backend API with both public and protected endpoints
2. Create the administrative web portal with authentication
3. Integrate read-only features into the Wix website using Velo
4. Set up hosting for the backend API and administrative portal
5. Implement proper security measures (HTTPS, secure authentication)
6. Test the integration between all components

## Technology Stack
- **Backend**: Python with Flask/FastAPI
- **Database**: SQLite (existing) or PostgreSQL for scaling
- **Authentication**: JWT (JSON Web Tokens)
- **Public Frontend**: Wix with Velo
- **Admin Frontend**: HTML/CSS/JavaScript (potentially React or Vue.js)
- **Hosting**: Heroku, Render, AWS, or similar service

This solution provides a balanced approach that leverages the existing tournament rating system while providing both public accessibility and secure administrative capabilities.
