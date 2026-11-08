import React, { useState, useEffect } from 'react';
import { API_BASE_URL } from '../config/api';
import { Player } from '../types/player';

const Leaderboard: React.FC<{ onPlayerClick?: (playerId: number) => void }> = ({ onPlayerClick }) => {
  const [players, setPlayers] = useState<Player[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerms, setSearchTerms] = useState<Record<string, string>>({
    Pro: '',
    Am: '',
    Junior: ''
  });

  useEffect(() => {
    fetchPlayers();
  }, []);

  const fetchPlayers = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/putt/players`, { credentials: 'include' });
      if (response.ok) {
        const data = await response.json();
        setPlayers(data);
      }
    } catch (error) {
      console.error('Failed to fetch players:', error);
    } finally {
      setLoading(false);
    }
  };

  const groupedPlayers = players.reduce((acc, player) => {
    if (player.seasonal_points <= 0) return acc;
    if (!acc[player.division]) acc[player.division] = [];
    acc[player.division].push(player);
    return acc;
  }, {} as Record<string, Player[]>);

  // Sort each division by points (descending) and filter by search
  const getFilteredPlayers = (division: string) => {
    const divisionPlayers = groupedPlayers[division] || [];
    const searchTerm = searchTerms[division].toLowerCase();
    
    return divisionPlayers
      .filter(player => {
        const name = (player.nickname || player.player_name).toLowerCase();
        return name.includes(searchTerm);
      })
      .sort((a, b) => b.seasonal_points - a.seasonal_points);
  };

  const handleSearchChange = (division: string, value: string) => {
    setSearchTerms(prev => ({ ...prev, [division]: value }));
  };

  const activeDivisions = ['Pro', 'Am', 'Junior'].filter(d => (groupedPlayers[d] || []).length > 0);

  if (loading) return <div className="loading">Loading leaderboard...</div>;

  return (
    <div className="leaderboard">
      <div className="page-header">
        <h2>Leaderboard</h2>
      </div>

      {activeDivisions.length === 0 ? (
        <div className="empty-state">
          The season hasn't started yet, but when it does check back here to see all of the divisional standings.
        </div>
      ) : (
        <div className="divisions-container">
          {activeDivisions.map(division => {
            const filteredPlayers = getFilteredPlayers(division);
            return (
              <div key={division} className="division-column">
                <h3>{division} Division</h3>
                <input
                  type="text"
                  placeholder="Search players..."
                  value={searchTerms[division]}
                  onChange={(e) => handleSearchChange(division, e.target.value)}
                  className="search-input"
                />
                <div className="table-scroll">
                  <table className="leaderboard-table">
                    <thead>
                      <tr>
                        <th>Rank</th>
                        <th>Player</th>
                        <th>Points</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredPlayers.map((player, index) => (
                        <tr
                          key={player.player_id}
                          className={onPlayerClick ? 'clickable-row' : ''}
                          onClick={() => onPlayerClick?.(player.player_id)}
                          role={onPlayerClick ? 'button' : undefined}
                          tabIndex={onPlayerClick ? 0 : undefined}
                          aria-label={onPlayerClick ? `View ${player.nickname || player.player_name}, rank ${index + 1}, ${player.seasonal_points} points` : undefined}
                          onKeyDown={onPlayerClick ? (e) => {
                            if (e.key === 'Enter' || e.key === ' ') {
                              e.preventDefault();
                              onPlayerClick(player.player_id);
                            }
                          } : undefined}
                        >
                          <td>{index + 1}</td>
                          <td>{player.nickname || player.player_name}</td>
                          <td>{player.seasonal_points}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default Leaderboard;
