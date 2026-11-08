import React from 'react';
import Match from './Match';
import { Match as MatchType, Team } from '../types/tournament';

interface BracketProps {
  matches: MatchType[];
  allMatches: MatchType[];
  teams: Team[];
  players: any[];
  title: string;
  onStartMatch?: (matchId: number) => void;
  onScoreMatch?: (matchId: number, team1Score: number, team2Score: number) => void;
}

const Bracket: React.FC<BracketProps> = ({ matches, allMatches, teams, players, title, onStartMatch, onScoreMatch }) => {
  const rounds = matches.reduce((acc, match) => {
    if (!acc[match.round_number]) acc[match.round_number] = [];
    acc[match.round_number].push(match);
    return acc;
  }, {} as Record<number, MatchType[]>);

  return (
    <div className="bracket">
      <h1>{title}</h1>
      <div className="rounds">
        {Object.entries(rounds).map(([round, roundMatches]) => (
          <div key={round} className="round">
            <h4>Round {round}</h4>
            {roundMatches.map(match => (
              <Match key={match.match_id} match={match} allMatches={allMatches} teams={teams} players={players} onStartMatch={onStartMatch} onScoreMatch={onScoreMatch} />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
};

export default Bracket;
