import { Team } from '../types/tournament';

export const getTeamDisplayName = (team: Team): string => {
  const player1Name = team.player1_nickname || team.player1_name || `Player ${team.player1_id}`;
  const player2Name = team.player2_id ? (team.player2_nickname || team.player2_name || `Player ${team.player2_id}`) : '';
  
  return team.is_ghost_team ? player1Name : `${player1Name} & ${player2Name}`;
};

export const findTeamById = (teams: Team[], teamId?: number | null): Team | undefined => {
  if (!teamId) return undefined;
  return teams.find(t => t.team_id === teamId);
};

export const getTeamName = (teams: Team[], teamId?: number | null): string => {
  if (!teamId) return 'TBD';
  const team = findTeamById(teams, teamId);
  if (!team) return 'TBD';
  return getTeamDisplayName(team);
};
