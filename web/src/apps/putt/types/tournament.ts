export interface Team {
  team_id: number;
  player1_id: number;
  player2_id?: number;
  is_ghost_team: boolean;
  seed_number: number;
  player1_name?: string;
  player1_nickname?: string;
  player2_name?: string;
  player2_nickname?: string;
  final_place?: number;
}

export interface Match {
  match_id: number;
  match_order: number;
  round_type: 'Winners' | 'Losers' | 'Championship';
  round_number: number;
  stage_type?: string;
  team1_id?: number;
  team2_id?: number;
  team1_score?: number;
  team2_score?: number;
  match_status: string;
  winner_advances_to_match_id?: number;
  loser_advances_to_match_id?: number;
  station_assignment?: number;
  team1?: Team;
  team2?: Team;
}

export interface Tournament {
  id: number;
  name: string;
  teams: Team[];
  matches: Match[];
}
