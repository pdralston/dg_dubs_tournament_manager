-- DG Dubs Database Schema
-- Run against the existing RDS instance to create the dg_dubs schema

CREATE DATABASE IF NOT EXISTS dg_dubs;
USE dg_dubs;

CREATE TABLE players (
    player_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    rating DECIMAL(8,2) NOT NULL DEFAULT 1000.00,
    tournaments_played INT NOT NULL DEFAULT 0,
    is_club_member BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE tournaments (
    tournament_id INT AUTO_INCREMENT PRIMARY KEY,
    date DATE NOT NULL,
    course VARCHAR(100),
    team_count INT NOT NULL,
    status ENUM('Pending', 'Scheduled', 'Completed') DEFAULT 'Scheduled',
    ace_pot_paid BOOLEAN DEFAULT FALSE,
    ace_pot_paid_to INT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ace_pot_paid_to) REFERENCES players(player_id)
);

CREATE TABLE teams (
    team_id INT AUTO_INCREMENT PRIMARY KEY,
    tournament_id INT NOT NULL,
    player1_id INT NOT NULL,
    player2_id INT NULL,
    is_ghost_team BOOLEAN DEFAULT FALSE,
    position INT NOT NULL,
    expected_position DECIMAL(6,2) NOT NULL,
    score INT NOT NULL,
    team_rating DECIMAL(8,2) NOT NULL,
    FOREIGN KEY (tournament_id) REFERENCES tournaments(tournament_id),
    FOREIGN KEY (player1_id) REFERENCES players(player_id),
    FOREIGN KEY (player2_id) REFERENCES players(player_id)
);

CREATE TABLE player_history (
    history_id INT AUTO_INCREMENT PRIMARY KEY,
    player_id INT NOT NULL,
    tournament_id INT NOT NULL,
    old_rating DECIMAL(8,2) NOT NULL,
    new_rating DECIMAL(8,2) NOT NULL,
    position INT NOT NULL,
    expected_position DECIMAL(6,2) NOT NULL,
    score INT NOT NULL,
    with_ghost BOOLEAN NOT NULL DEFAULT FALSE,
    FOREIGN KEY (player_id) REFERENCES players(player_id),
    FOREIGN KEY (tournament_id) REFERENCES tournaments(tournament_id)
);

CREATE TABLE tournament_participants (
    participant_id INT AUTO_INCREMENT PRIMARY KEY,
    tournament_id INT NOT NULL,
    player_id INT NOT NULL,
    ace_pot_buy_in BOOLEAN DEFAULT FALSE,
    UNIQUE KEY uq_tournament_player (tournament_id, player_id),
    FOREIGN KEY (tournament_id) REFERENCES tournaments(tournament_id),
    FOREIGN KEY (player_id) REFERENCES players(player_id)
);

-- Ace pot tracker stores a running ledger with a balance column
-- cap_amount is stored in ace_pot_config; current = min(balance, cap), reserve = max(0, balance - cap)
CREATE TABLE ace_pot_tracker (
    entry_id INT AUTO_INCREMENT PRIMARY KEY,
    date DATE NOT NULL,
    description VARCHAR(255) NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    balance DECIMAL(10,2) NOT NULL,
    tournament_id INT NULL,
    player_id INT NULL,
    FOREIGN KEY (tournament_id) REFERENCES tournaments(tournament_id),
    FOREIGN KEY (player_id) REFERENCES players(player_id)
);

CREATE TABLE ace_pot_config (
    id INT PRIMARY KEY DEFAULT 1,
    cap_amount DECIMAL(10,2) NOT NULL DEFAULT 100.00,
    CONSTRAINT single_row CHECK (id = 1)
);

INSERT INTO ace_pot_config (id, cap_amount) VALUES (1, 100.00);

-- Seasons table for archiving (same pattern as dgputt)
CREATE TABLE seasons (
    season_id INT AUTO_INCREMENT PRIMARY KEY,
    season_name VARCHAR(100) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE tournaments ADD COLUMN season_id INT NULL,
    ADD FOREIGN KEY (season_id) REFERENCES seasons(season_id);

CREATE INDEX idx_player_name ON players(name);
CREATE INDEX idx_tournament_date ON tournaments(date);
CREATE INDEX idx_player_history_player ON player_history(player_id);
CREATE INDEX idx_player_history_tournament ON player_history(tournament_id);
CREATE INDEX idx_team_tournament ON teams(tournament_id);
CREATE INDEX idx_tournament_season ON tournaments(season_id);
