import React from 'react';
import { Match as MatchType, Team } from '../types/tournament';
import { getTeamName, getTeamDisplayName, findTeamById } from '../utils/teamUtils';

interface BracketViewProps {
  matches: MatchType[];
  teams: Team[];
  title: string;
  allMatches?: MatchType[];
}

const BracketView: React.FC<BracketViewProps> = ({ matches, teams, title, allMatches }) => {
  const rounds = matches.reduce((acc, match) => {
    if (!acc[match.round_number]) acc[match.round_number] = [];
    acc[match.round_number].push(match);
    return acc;
  }, {} as Record<number, MatchType[]>);

  const getTeamName = (teamId: number): string => {
    const team = teams.find(t => t.team_id === teamId);
    if (team) {
      const player1Name = team.player1_nickname || team.player1_name || `Player ${team.player1_id}`;
      const player2Name = team.player2_id ? (team.player2_nickname || team.player2_name || `Player ${team.player2_id}`) : '';
      return team.is_ghost_team ? player1Name : `${player1Name} & ${player2Name}`;
    }
    return `Team ${teamId}`;
  };

  const getTeamDisplay = (teamId?: number, match?: MatchType, isTeam1: boolean = true): string => {
    if (teamId) {
      const team = teams.find(t => t.team_id === teamId);
      if (team && team.player1_name) {
        return team.player2_name ? `${team.player1_name} & ${team.player2_name}` : team.player1_name;
      }
      return `Team ${teamId}`;
    }
    
    if (!match) return 'ERROR';
    
    // Find matches that feed into this match
    const feedingMatches = (allMatches || matches).filter(m => 
      m.winner_advances_to_match_id === match.match_id || 
      m.loser_advances_to_match_id === match.match_id
    ).sort((a, b) => a.match_order - b.match_order);
    
    if (feedingMatches.length === 0) {
      return 'ERROR';
    }
    
    if (feedingMatches.length === 1) {
      const feedingMatch = feedingMatches[0];
      const isWinnerAdvancing = feedingMatch.winner_advances_to_match_id === match.match_id;
      
      // For matches with one team already seeded, the empty slot gets the feeding match result
      if (match.team1_id && !match.team2_id) {
        return isTeam1 ? getTeamName(match.team1_id) : `${isWinnerAdvancing ? 'Winner' : 'Loser'} ${feedingMatch.match_order}`;
      } else if (!match.team1_id && match.team2_id) {
        return isTeam1 ? `${isWinnerAdvancing ? 'Winner' : 'Loser'} ${feedingMatch.match_order}` : getTeamName(match.team2_id);
      } else {
        // Neither team seeded yet
        if (isTeam1) {
          return `${isWinnerAdvancing ? 'Winner' : 'Loser'} ${feedingMatch.match_order}`;
        } else {
          if (match.round_type === 'Losers') {
            return 'BYE';
          } else {
            return 'BYE';
          }
        }
      }
    }
    
    const feedingMatch = isTeam1 ? feedingMatches[0] : feedingMatches[1];
    const isWinnerAdvancing = feedingMatch.winner_advances_to_match_id === match.match_id;
    return `${isWinnerAdvancing ? 'Winner' : 'Loser'} ${feedingMatch.match_order}`;
  };

  const getWinner = (match: MatchType) => {
    if (match.match_status !== 'Completed') return null;
    if (match.team1_score !== null && match.team1_score !== undefined && 
        match.team2_score !== null && match.team2_score !== undefined) {
      return match.team1_score > match.team2_score ? match.team1_id : match.team2_id;
    }
    return null;
  };

  return (
    <div className="bracket-view">
      <h1>{title}</h1>
      <div className="rounds">
        {Object.entries(rounds)
          .sort(([a], [b]) => parseInt(a) - parseInt(b))
          .map(([roundNum, roundMatches]) => (
            <div key={roundNum} className="round">
              <h4>Round {roundNum}</h4>
              {roundMatches.map(match => {
                const winner = getWinner(match);
                return (
                  <div key={match.match_id} className="match">
                    <div className="match-header">
                      <span className="match-number">Match {match.match_id}</span>
                    </div>
                    <div className="team-container">
                      <div className={`team ${winner === match.team1_id ? 'winner' : ''}`}>
                        <span className="team-name">{getTeamDisplay(match.team1_id, match, true)}</span>
                        <span className="team-score">{match.team1_score ?? ''}</span>
                      </div>
                      <div className={`team ${winner === match.team2_id ? 'winner' : ''}`}>
                        <span className="team-name">{getTeamDisplay(match.team2_id, match, false)}</span>
                        <span className="team-score">{match.team2_score ?? ''}</span>
                      </div>
                    </div>
                    <div className={`match-status ${match.match_status.toLowerCase().replace('_', '-')}`}>
                      {match.match_status.replace('_', ' ')}
                    </div>
                  </div>
                );
              })}
            </div>
          ))}
      </div>
    </div>
  );
};

export default BracketView;
