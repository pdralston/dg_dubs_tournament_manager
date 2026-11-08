import React, { useState } from 'react';
import { Match as MatchType, Team } from '../types/tournament';
import { getTeamName, getTeamDisplayName, findTeamById } from '../utils/teamUtils';

interface MatchProps {
  match: MatchType;
  allMatches: MatchType[];
  teams: Team[];
  players: any[];
  onStartMatch?: (matchId: number) => void;
  onScoreMatch?: (matchId: number, team1Score: number, team2Score: number) => void;
}

const Match: React.FC<MatchProps> = ({ match, allMatches, teams, players, onStartMatch, onScoreMatch }) => {
  const [showScorePopup, setShowScorePopup] = useState(false);
  const [team1Score, setTeam1Score] = useState('');
  const [team2Score, setTeam2Score] = useState('');

  const handleScoreSubmit = () => {
    const score1 = parseInt(team1Score);
    const score2 = parseInt(team2Score);
    if (!isNaN(score1) && !isNaN(score2) && onScoreMatch) {
      onScoreMatch(match.match_id, score1, score2);
      setShowScorePopup(false);
      setTeam1Score('');
      setTeam2Score('');
    }
  };

  const isByeMatch = () => {
    return match.team2_id === null && match.match_status === 'Scheduled';
  };


  const getWinner = () => {
    if (match.match_status !== 'Completed') {
      return null;
    }
    if (match.team1_score !== null && match.team1_score !== undefined && 
        match.team2_score !== null && match.team2_score !== undefined) {
      return match.team1_score > match.team2_score ? match.team1_id : match.team2_id;
    }
    return null;
  };

  const getTeamDisplay = (teamId?: number, isTeam1: boolean = true) => {
    if (teamId) {
      const team = findTeamById(teams, teamId);
      if (team) {
        return getTeamDisplayName(team);
      }
      return `Team ${teamId}`;
    }
    
    // Find matches that feed into this match
    const feedingMatches = allMatches.filter(m => 
      m.winner_advances_to_match_id === match.match_id || 
      m.loser_advances_to_match_id === match.match_id
    ).sort((a, b) => a.match_order - b.match_order);
    
    if (feedingMatches.length === 0) {
      return 'TBD';
    }
    
    // Find which feeding matches are still pending
    const pendingMatches = feedingMatches.filter(m => m.match_status !== 'Completed');
    
    if (pendingMatches.length === 0) {
      return 'BYE'; // All feeding matches complete, team should be assigned or there was only one feeding match before
    }
    
    if (feedingMatches.length === 1) {
      const feedingMatch = feedingMatches[0];
      const isWinnerAdvancing = feedingMatch.winner_advances_to_match_id === match.match_id;

      if (isTeam1 || match.team1_id) {
        return `${isWinnerAdvancing ? 'Winner' : 'Loser'} ${feedingMatch.match_order}`;
      } else {
        return 'BYE';
      }
  }
    
    // Multiple feeding matches - show the first pending one for team1, second for team2
    if (isTeam1 && pendingMatches.length > 0) {
      const feedingMatch = pendingMatches[0];
      const isWinnerAdvancing = feedingMatch.winner_advances_to_match_id === match.match_id;
      return `${isWinnerAdvancing ? 'Winner' : 'Loser'} ${feedingMatch.match_order}`;
    } else if (!isTeam1 && pendingMatches.length > 1) {
      const feedingMatch = pendingMatches[1];
      const isWinnerAdvancing = feedingMatch.winner_advances_to_match_id === match.match_id;
      return `${isWinnerAdvancing ? 'Winner' : 'Loser'} ${feedingMatch.match_order}`;
    } else if (!isTeam1 && pendingMatches.length === 1) {
      // Only one pending match left, show it for team2 if team1 is already filled
      const feedingMatch = pendingMatches[0];
      const isWinnerAdvancing = feedingMatch.winner_advances_to_match_id === match.match_id;
      return `${isWinnerAdvancing ? 'Winner' : 'Loser'} ${feedingMatch.match_order}`;
    }
    
    return 'TBD';
  };

  const winner = getWinner();

  // Debug logging
  if (match.match_order === 1) {
    console.log('Match 1 status:', match.match_status, 'onScoreMatch exists:', !!onScoreMatch);
  }

  const formatTeamName = (teamName: string) => {
    return teamName.split(' & ').map((name, index, array) => (
      <span key={index}>
        {name}
        {index < array.length - 1 && <span className="team-separator"> & </span>}
      </span>
    ));
  };

  const renderMatchHeader = () => {
    const matchNumber = `Match ${match.match_order}`;
    
    switch (match.match_status) {
      case 'Scheduled':
        return (
          <>
            <span className="match-number">{matchNumber}</span>
            <span className="match-status-text scheduled">Scheduled</span>
          </>
        );
      case 'In_Progress':
        return (
          <>
            <div style={{ display: 'flex', alignItems: 'center' }}>
              <span className="match-number">{matchNumber}</span>
              {match.station_assignment && (
                <span className="station-bubble">Station {match.station_assignment}</span>
              )}
            </div>
            <span className="match-status-text in-progress">In Progress</span>
          </>
        );
      case 'Completed':
        return (
          <>
            <span className="match-number">{matchNumber} | <span className="match-status-text completed">Completed</span></span>
            <span className="match-status-text score">SCORE</span>
          </>
        );
      case 'Pending':
      default:
        return <span className="match-number">{matchNumber}</span>;
    }
  };

  return (
    <div className={`match ${match.match_status.toLowerCase().replace('_', '-')}`}>
      <div className="match-header">
        {renderMatchHeader()}
      </div>
      <div className="team-container">
        <div className={`team ${winner && winner === match.team1_id ? 'winner' : ''}`}>
          <span className="team-name">
            {formatTeamName(getTeamDisplay(match.team1_id, true))}
            {winner && winner === match.team1_id && <span className="trophy-icon">🏆</span>}
          </span>
          {match.team1_score !== undefined && match.team1_score !== null && (
            <span className="team-score">{match.team1_score}</span>
          )}
        </div>
        <div className={`team ${winner && winner === match.team2_id ? 'winner' : ''}`}>
          <span className="team-name">
            {formatTeamName(getTeamDisplay(match.team2_id, false))}
            {winner && winner === match.team2_id && <span className="trophy-icon">🏆</span>}
          </span>
          {match.team2_score !== undefined && match.team2_score !== null && (
            <span className="team-score">{match.team2_score}</span>
          )}
        </div>
      </div>
      {match.match_status === 'Scheduled' && onStartMatch && !isByeMatch() && (
        <div className="start-overlay" onClick={() => onStartMatch(match.match_id)}>
          ▶ Start
        </div>
      )}

      {match.match_status === 'In_Progress' && onScoreMatch && (
        <div className="score-overlay" onClick={() => {
          console.log('Score overlay clicked for match', match.match_id);
          setShowScorePopup(true);
        }}>
          📊 Score
        </div>
      )}

      {match.match_status === 'Completed' && onScoreMatch && (
        <div className="edit-overlay" onClick={() => {
          setTeam1Score(match.team1_score?.toString() || '');
          setTeam2Score(match.team2_score?.toString() || '');
          setShowScorePopup(true);
        }}>
          ✏️ Edit
        </div>
      )}
      
      {showScorePopup && (
        <div className="score-popup-overlay">
          <div className="score-popup" onClick={(e) => e.stopPropagation()}>
            <h4>{match.match_status === 'Completed' ? 'Edit Scores' : 'Enter Scores'}</h4>
            <div className="score-input">
              <label>{getTeamDisplay(match.team1_id, true)}</label>
              <input 
                type="number" 
                value={team1Score} 
                onChange={(e) => setTeam1Score(e.target.value)}
                min="0"
              />
            </div>
            <div className="score-input">
              <label>{getTeamDisplay(match.team2_id, false)}</label>
              <input 
                type="number" 
                value={team2Score} 
                onChange={(e) => setTeam2Score(e.target.value)}
                min="0"
              />
            </div>
            <div className="score-buttons">
              <button onClick={() => setShowScorePopup(false)}>Cancel</button>
              <button onClick={handleScoreSubmit}>
                {match.match_status === 'Completed' ? 'Update' : 'Submit'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Match;
