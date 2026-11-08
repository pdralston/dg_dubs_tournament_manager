export interface Player {
  name: string;
  rating: number;
  tournaments_played: number;
  is_club_member?: boolean;
}

export interface PlayerHistory {
  date: string;
  position: number;
  expected_position: number;
  old_rating: number;
  new_rating: number;
  change: number;
  with_ghost: boolean;
  score?: number;
}

export interface PlayerDetail extends Player {
  history: PlayerHistory[];
}

export interface TeamResult {
  team: string[];
  position: number;
  expected_position: number;
  score: number;
  team_rating: number;
}

export interface Tournament {
  id?: number;
  date: string;
  course: string;
  teams: number;
  results: TeamResult[];
}

export interface GeneratedTeam {
  player1: string;
  player2: string;
  team_rating: number;
  expected_position: number;
}

export interface AcePotBalance {
  total: number;
  current: number;
  reserve: number;
}

export interface AcePotConfig {
  cap_amount: number;
}

export interface AcePotEntry {
  id: number;
  date: string;
  description: string;
  amount: number;
  balance: number;
  tournament_id?: number;
  player_name?: string;
}

export interface User {
  user_id: number;
  username: string;
  role: string;
}
