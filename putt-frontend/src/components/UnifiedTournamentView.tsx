import React, { useEffect, useState, useCallback } from 'react';
import { API_BASE_URL } from '../config/api';
import Bracket from './Bracket';
import { Tournament, Match } from '../types/tournament';
import { getTeamName } from '../utils/teamUtils';
import { useWebSocket } from '../hooks/useWebSocket';

interface UnifiedTournamentViewProps {
  tournamentId: number;
  onBack?: () => void;
  showManagementActions?: boolean;
}

const UnifiedTournamentView: React.FC<UnifiedTournamentViewProps> = ({ 
  tournamentId, 
  onBack, 
  showManagementActions = false 
}) => {
  const [tournament, setTournament] = useState<Tournament | null>(null);
  const [tournamentData, setTournamentData] = useState<any>(null);
  const [tournamentStatus, setTournamentStatus] = useState<string>('');
  const [showCompletionOverlay, setShowCompletionOverlay] = useState(false);
  const [acePotBalance, setAcePotBalance] = useState<number>(0);
  const [accentText, setAccentText] = useState('');
  const [showScorePopup, setShowScorePopup] = useState(false);
  const [selectedMatch, setSelectedMatch] = useState<Match | null>(null);
  const [team1Score, setTeam1Score] = useState('');
  const [team2Score, setTeam2Score] = useState('');

  const accentTexts = ['Shoot Well', 'Bang Chains', 'Aim Straight', 'Double Up'];

  const fetchTournamentData = useCallback(async () => {
    try {
      const [matches, teams, tournamentData, acePotData] = await Promise.all([
        fetch(`${API_BASE_URL}/api/putt/tournaments/${tournamentId}/matches`, { credentials: 'include' }).then(res => res.json()),
        fetch(`${API_BASE_URL}/api/putt/tournaments/${tournamentId}/teams`, { credentials: 'include' }).then(res => res.json()),
        fetch(`${API_BASE_URL}/api/putt/tournaments?id=${tournamentId}`, { credentials: 'include' }).then(res => res.json()),
        fetch(`${API_BASE_URL}/api/putt/ace-pot`, { credentials: 'include' }).then(res => res.json())
      ]);
      
      setTournament({ id: tournamentId, name: `Tournament ${tournamentId}`, teams, matches });
      setTournamentData(tournamentData);
      setTournamentStatus(tournamentData.status);
      setShowCompletionOverlay(tournamentData.status === 'Completed');
      
      const totalBalance = acePotData.reduce((sum: number, entry: any) => sum + entry.amount, 0);
      setAcePotBalance(totalBalance);
    } catch (error) {
      console.error('Failed to fetch tournament data:', error);
    }
  }, [tournamentId]);

  // WebSocket for real-time updates
  useWebSocket({
    tournamentId,
    onMatchUpdate: fetchTournamentData
  });

  useEffect(() => {
    // Set random accent text
    const randomText = accentTexts[Math.floor(Math.random() * accentTexts.length)];
    setAccentText(randomText);

    // Initial data fetch
    fetchTournamentData();
  }, [fetchTournamentData]);

  const getMatchesInProgress = (): Match[] => {
    if (!tournament) return [];
    return tournament.matches.filter(match => match.match_status === 'In_Progress');
  };

  const getTeamDisplayName = (teamId?: number | null): string => {
    if (!tournament) return 'TBD';
    return getTeamName(tournament.teams, teamId);
  };

  const handleScoreMatch = async (matchId: number, team1Score: number, team2Score: number) => {
    if (!showManagementActions) return;
    
    // Check if this is the last match that would complete the tournament
    const match = tournament?.matches.find(m => m.match_id === matchId);
    const isLastMatch = match?.round_type === 'Championship' && (
      match.round_number === 1 || // Second championship match
      (match.round_number === 0 && team1Score > team2Score) // First championship match with WB winner winning
    );
    
    if (isLastMatch) {
      const confirmed = window.confirm(
        'This will complete and finalize the tournament. Are you sure you want to proceed?'
      );
      if (!confirmed) return;
    }
    
    try {
      const response = await fetch(`${API_BASE_URL}/api/putt/tournaments/${tournamentId}/matches/${matchId}/score`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ team1_score: team1Score, team2_score: team2Score })
      });
      
      if (response.ok) {
        const [matches, teams, tournamentData] = await Promise.all([
          fetch(`${API_BASE_URL}/api/putt/tournaments/${tournamentId}/matches`, { credentials: 'include' }).then(res => res.json()),
          fetch(`${API_BASE_URL}/api/putt/tournaments/${tournamentId}/teams`, { credentials: 'include' }).then(res => res.json()),
          fetch(`${API_BASE_URL}/api/putt/tournaments?id=${tournamentId}`, { credentials: 'include' }).then(res => res.json())
        ]);
        setTournament({ id: tournamentId, name: `Tournament ${tournamentId}`, teams, matches });
        setTournamentData(tournamentData);
        setTournamentStatus(tournamentData.status);
        setShowCompletionOverlay(tournamentData.status === 'Completed');
      } else {
        const error = await response.json();
        alert(`Error scoring match: ${error.error || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Failed to score match:', error);
      alert('Network error: Failed to score match. Please try again.');
    }
  };

  const handleStartMatch = async (matchId: number) => {
    if (!showManagementActions) return;
    
    try {
      const response = await fetch(`${API_BASE_URL}/api/putt/tournaments/${tournamentId}/matches/${matchId}/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include'
      });
      
      if (response.ok) {
        const [matches, teams] = await Promise.all([
          fetch(`${API_BASE_URL}/api/putt/tournaments/${tournamentId}/matches`, { credentials: 'include' }).then(res => res.json()),
          fetch(`${API_BASE_URL}/api/putt/tournaments/${tournamentId}/teams`, { credentials: 'include' }).then(res => res.json())
        ]);
        setTournament({ id: tournamentId, name: `Tournament ${tournamentId}`, teams, matches });
      } else {
        const error = await response.json();
        alert(`Error starting match: ${error.error || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Failed to start match:', error);
      alert('Network error: Failed to start match. Please try again.');
    }
  };

  const handleStartTournament = async () => {
    if (!showManagementActions) return;
    
    try {
      const response = await fetch(`${API_BASE_URL}/api/putt/tournaments/${tournamentId}/status`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ status: 'In_Progress' })
      });

      if (response.ok) {
        setTournamentStatus('In_Progress');
      } else {
        const error = await response.json();
        alert(`Error starting tournament: ${error.error || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Failed to start tournament:', error);
      alert('Network error: Failed to start tournament. Please try again.');
    }
  };

  const getTop4Teams = () => {
    if (!tournament) return [];
    return tournament.teams
      .filter(t => t.final_place && t.final_place <= 4)
      .sort((a, b) => (a.final_place || 999) - (b.final_place || 999));
  };

  const calculatePayout = (place: number, totalParticipants: number, isUndefeated: boolean = false) => {
    switch (place) { 
      case 1:
        return tournamentData.first_payout;
      case 2: return tournamentData.second_payout;
      default: return 0;
    }
  };

  const isTeamUndefeated = (teamId: number): boolean => {
    if (!tournament) return false;
    
    const teamMatches = tournament.matches.filter(m => 
      (m.team1_id === teamId || m.team2_id === teamId) && 
      m.match_status === 'Completed' && 
      m.team2_id !== null
    );
    
    return teamMatches.every(match => {
      if (match.team1_score === undefined || match.team2_score === undefined) return false;
      
      if (match.team1_id === teamId) {
        return match.team1_score > match.team2_score;
      } else {
        return match.team2_score > match.team1_score;
      }
    });
  };

  const getAward = (place: number, payout: number) => {
    if (place === 1 || place === 2) {
      return `$${payout}`;
    } else if (place === 3) {
      return '2 Crowlers from Hapas Brewing';
    } else if (place === 4) {
      return 'Free entry next week';
    }
    return '';
  };

  const handleActiveMatchClick = (match: Match) => {
    if (!showManagementActions) return;
    setSelectedMatch(match);
    setTeam1Score(match.team1_score?.toString() || '');
    setTeam2Score(match.team2_score?.toString() || '');
    setShowScorePopup(true);
  };

  const handleScoreSubmit = async () => {
    if (!selectedMatch) return;
    const score1 = parseInt(team1Score);
    const score2 = parseInt(team2Score);
    if (!isNaN(score1) && !isNaN(score2)) {
      await handleScoreMatch(selectedMatch.match_id, score1, score2);
      setShowScorePopup(false);
      setTeam1Score('');
      setTeam2Score('');
      setSelectedMatch(null);
    }
  };

  const matchesInProgress = getMatchesInProgress();
  
  useEffect(() => {
    const updateHeights = () => {
      // Update header height
      const header = document.querySelector('.App-header');
      if (header) {
        const headerHeight = header.getBoundingClientRect().height;
        document.documentElement.style.setProperty('--header-height', `${headerHeight}px`);
      }
      
      // Update matches bar height
      const matchesBar = document.querySelector('.matches-in-progress');
      if (matchesBar) {
        const height = matchesBar.getBoundingClientRect().height;
        document.documentElement.style.setProperty('--matches-bar-height', `${height}px`);
      }
    };

    // Initial calculation
    updateHeights();
    
    // Watch for resize changes
    const header = document.querySelector('.App-header');
    const matchesBar = document.querySelector('.matches-in-progress');
    
    const resizeObserver = new ResizeObserver(updateHeights);
    if (header) resizeObserver.observe(header);
    if (matchesBar) resizeObserver.observe(matchesBar);
    
    // Also listen for window resize
    window.addEventListener('resize', updateHeights);
    
    return () => {
      resizeObserver.disconnect();
      window.removeEventListener('resize', updateHeights);
    };
  }, [matchesInProgress.length]);

  if (!tournament) {
    return <div className="loading">Loading tournament...</div>;
  }

  const formatTeamName = (teamName: string) => {
    return teamName.split(' & ').map((name, index, array) => (
      <span key={index}>
        {name}
        {index < array.length - 1 && <span className="team-separator"> & </span>}
      </span>
    ));
  };
  const winnersMatches = tournament.matches.filter(m => m.round_type === 'Winners');
  const losersMatches = tournament.matches.filter(m => m.round_type === 'Losers');
  const championshipMatches = tournament.matches.filter(m => m.round_type === 'Championship');

  return (
    <div className="tournament-view">
      <div className="accent-text">{accentText}</div>
      {matchesInProgress.length > 0 && (
        <div className="matches-in-progress">
          <h5>Matches in Progress</h5>
          <div className="active-matches">
            {matchesInProgress.map(match => (
              <div 
                key={match.match_id} 
                className={`active-match ${showManagementActions ? 'clickable' : ''}`}
                onClick={() => handleActiveMatchClick(match)}
              >
                <div className="station">
                  Station {match.station_assignment}
                  <img src="/dg-basket-grn.svg" alt="Basket" />
                </div>
                <div className="teams">
                  <div className="team-row">
                    {formatTeamName(getTeamDisplayName(match.team1_id))}
                  </div>
                  <div className="team-row">
                    {formatTeamName(getTeamDisplayName(match.team2_id))}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
      
      {onBack && (
        <div className="back-button-container">
          <button className="back-button" onClick={onBack}>
            <img src="/back-arrow-circle.png" alt="Back" />
            Back to Tournaments
          </button>
        </div>
      )}
      
      <div className={`tournament-content ${matchesInProgress.length > 0 ? 'with-matches-in-progress' : ''}`} style={{ position: 'relative' }}>
        {showManagementActions && tournamentStatus === 'Scheduled' && (
          <div className="tournament-overlay">
            <div className="overlay-content">
              <h2>Tournament Ready to Start</h2>
              <p>This tournament is scheduled and ready to begin.</p>
              <button className="start-tournament-button" onClick={handleStartTournament}>
                Start Tournament
              </button>
            </div>
          </div>
        )}
        
        {tournamentStatus === 'Completed' && showCompletionOverlay && (
          <div className="tournament-overlay">
            <div className="overlay-content">
              <h2>Tournament Complete!</h2>
              <h3>Top 4 Finishers</h3>
              <div className="top-4-results">
                {getTop4Teams().map(team => {
                  const isUndefeated = isTeamUndefeated(team.team_id);
                  const payout = calculatePayout(team.final_place || 0, tournament.teams.length * 2, isUndefeated);
                  return (
                    <div key={team.team_id} className={`place-result ${isUndefeated && team.final_place === 1 ? 'undefeated-winner' : ''}`}>
                      <div className="place-number">{team.final_place}</div>
                      <div className="team-name">{getTeamDisplayName(team.team_id)}</div>
                      {isUndefeated && team.final_place === 1 && <div className="ace-stamp">ACE</div>}
                      <div className="award">{getAward(team.final_place || 0, payout)}</div>
                    </div>
                  );
                })}
              </div>
              <button className="close-overlay-button" onClick={() => setShowCompletionOverlay(false)}>
                Close
              </button>
            </div>
          </div>
        )}
        
        <div className="brackets-container">
          <div className="main-brackets">
            <div className="winners-championship-container">
              {winnersMatches.length > 0 && (
                <Bracket 
                  matches={winnersMatches}
                  allMatches={tournament.matches}
                  teams={tournament.teams}
                  players={[]}
                  title="Winners Bracket"
                  onScoreMatch={showManagementActions && tournamentStatus === 'In_Progress' ? handleScoreMatch : undefined}
                  onStartMatch={showManagementActions && tournamentStatus === 'In_Progress' ? handleStartMatch : undefined}
                />
              )}
              {championshipMatches.filter(m => m.team1_id && m.team2_id).length > 0 && (
                <div className="championship-section">
                  <Bracket 
                    matches={championshipMatches}
                    allMatches={tournament.matches}
                    teams={tournament.teams}
                    players={[]}
                    title="🏆 Championship"
                    onScoreMatch={showManagementActions && tournamentStatus === 'In_Progress' ? handleScoreMatch : undefined}
                    onStartMatch={showManagementActions && tournamentStatus === 'In_Progress' ? handleStartMatch : undefined}
                  />
                </div>
              )}
            </div>
            {losersMatches.length > 0 && (
              <Bracket 
                matches={losersMatches}
                allMatches={tournament.matches}
                teams={tournament.teams}
                players={[]}
                title="Losers Bracket"
                onScoreMatch={showManagementActions && tournamentStatus === 'In_Progress' ? handleScoreMatch : undefined}
                onStartMatch={showManagementActions && tournamentStatus === 'In_Progress' ? handleStartMatch : undefined}
              />
            )}
          </div>
        </div>
      </div>
      
      {showScorePopup && selectedMatch && (
        <div className="score-popup-overlay">
          <div className="score-popup" onClick={(e) => e.stopPropagation()}>
            <h4>Score Match {selectedMatch.match_order}</h4>
            <div className="score-input">
              <label>{getTeamDisplayName(selectedMatch.team1_id)}</label>
              <input 
                type="number" 
                value={team1Score} 
                onChange={(e) => setTeam1Score(e.target.value)}
                min="0"
              />
            </div>
            <div className="score-input">
              <label>{getTeamDisplayName(selectedMatch.team2_id)}</label>
              <input 
                type="number" 
                value={team2Score} 
                onChange={(e) => setTeam2Score(e.target.value)}
                min="0"
              />
            </div>
            <div className="score-buttons">
              <button onClick={() => setShowScorePopup(false)}>Cancel</button>
              <button onClick={handleScoreSubmit}>Submit</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default UnifiedTournamentView;
