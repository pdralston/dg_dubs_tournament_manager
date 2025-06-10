# Disc Golf League Tournament Rating System API

This document describes the RESTful API endpoints available for the Disc Golf League Tournament Rating System.

## Base URL

All API endpoints are relative to the base URL of the web application.

## Players API

### Get All Players

**Endpoint:** `GET /api/players`

**Description:** Retrieves a list of all players and their ratings.

**Response:**
```json
[
  {
    "name": "Player Name",
    "rating": 1050.0,
    "tournaments_played": 5
  },
  ...
]
```

### Get Player Details

**Endpoint:** `GET /api/players/<name>`

**Description:** Retrieves detailed information about a specific player.

**Response:**
```json
{
  "name": "Player Name",
  "rating": 1050.0,
  "tournaments_played": 5,
  "history": [
    {
      "date": "2025-04-26",
      "position": 1,
      "expected_position": 2.0,
      "old_rating": 1000.0,
      "new_rating": 1050.0,
      "change": 50.0,
      "with_ghost": false
    },
    ...
  ]
}
```

### Add Player

**Endpoint:** `POST /api/players`

**Description:** Adds a new player to the system.

**Request Body:**
```json
{
  "name": "New Player",
  "rating": 1000.0
}
```

**Response:**
```json
{
  "name": "New Player",
  "rating": 1000.0,
  "tournaments_played": 0,
  "message": "Added player New Player with initial rating 1000.0"
}
```

## Tournaments API

### Get All Tournaments

**Endpoint:** `GET /api/tournaments`

**Description:** Retrieves a list of all tournaments.

**Response:**
```json
[
  {
    "date": "2025-04-26",
    "course": "Pine Valley",
    "teams": 4,
    "results": [
      {
        "team": ["Player1", "Player2"],
        "score": 52,
        "position": 1
      },
      ...
    ]
  },
  ...
]
```

### Record Tournament

**Endpoint:** `POST /api/tournaments`

**Description:** Records a new tournament.

**Request Body:**
```json
{
  "course": "Pine Valley",
  "date": "2025-04-26",
  "team_results": [
    {
      "player1": "Player1",
      "player2": "Player2",
      "score": 52
    },
    ...
  ]
}
```

**Response:**
```json
{
  "message": "Tournament recorded with 4 teams",
  "date": "2025-04-26",
  "course": "Pine Valley",
  "teams": 4
}
```

### Predict Tournament

**Endpoint:** `POST /api/predict`

**Description:** Predicts the outcome of a tournament.

**Request Body:**
```json
{
  "teams": [
    {
      "player1": "Player1",
      "player2": "Player2"
    },
    ...
  ],
  "par": 54
}
```

**Response:**
```json
[
  {
    "player1": "Player1",
    "player2": "Player2",
    "team_rating": 1025.0,
    "expected_position": 1.0,
    "predicted_score": 52.5
  },
  ...
]
```

### Generate Teams

**Endpoint:** `POST /api/teams`

**Description:** Generates balanced teams from a list of players.

**Request Body:**
```json
{
  "players": ["Player1", "Player2", "Player3", "Player4"],
  "allow_ghost": false
}
```

**Response:**
```json
[
  {
    "player1": "Player1",
    "player2": "Player4",
    "team_rating": 1025.0,
    "expected_position": 1.0
  },
  {
    "player1": "Player2",
    "player2": "Player3",
    "team_rating": 1025.0,
    "expected_position": 1.0
  }
]
```

## Storage API

### Get Storage Mode

**Endpoint:** `GET /api/storage`

**Description:** Gets the current storage mode.

**Response:**
```json
{
  "mode": "database",
  "file": "tournament_data.db"
}
```

### Update Storage Mode

**Endpoint:** `PUT /api/storage`

**Description:** Updates the storage mode.

**Request Body:**
```json
{
  "mode": "json"
}
```

**Response:**
```json
{
  "mode": "json",
  "file": "tournament_data.json",
  "message": "Switched to JSON storage"
}
```

## Error Handling

All API endpoints return appropriate HTTP status codes:

- `200 OK`: Request successful
- `201 Created`: Resource created successfully
- `400 Bad Request`: Invalid request parameters
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error

Error responses include a JSON object with an error message:

```json
{
  "error": "Error message"
}
```
