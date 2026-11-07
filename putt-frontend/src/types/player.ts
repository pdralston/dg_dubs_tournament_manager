export interface Player {
  player_id: number;
  player_name: string;
  nickname?: string;
  division: 'Pro' | 'Am' | 'Junior';
  seasonal_points: number;
  seasonal_cash: number;
}
