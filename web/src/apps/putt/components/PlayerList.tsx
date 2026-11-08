import React, { useState } from 'react';
import { Player } from '../types/player';

interface PlayerListProps {
  players: Player[];
  onPlayerClick: (player: Player) => void;
  onEditPlayer?: (player: Player) => void;
  searchTerm?: string;
}

const PlayerList: React.FC<PlayerListProps> = ({ players, onPlayerClick, onEditPlayer, searchTerm = '' }) => {
  const [divisionFilter, setDivisionFilter] = useState<string>('All');

  // Filter players by division and search term for display only
  const filteredPlayers = players
    .filter(p => divisionFilter === 'All' || p.division === divisionFilter)
    .filter(p =>
      !searchTerm ||
      p.player_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (p.nickname && p.nickname.toLowerCase().includes(searchTerm.toLowerCase()))
    );

  // Sort players alphabetically by name
  const sortedPlayers = filteredPlayers.sort((a, b) => 
    a.player_name.localeCompare(b.player_name)
  );

  // Calculate divisional rankings
  const getDivisionalRank = (player: Player): number => {
    const divisionPlayers = players
      .filter(p => p.division === player.division)
      .sort((a, b) => b.seasonal_points - a.seasonal_points);
    
    // Handle ties - players with same points get same rank
    let rank = 1;
    for (let i = 0; i < divisionPlayers.length; i++) {
      if (i > 0 && divisionPlayers[i].seasonal_points < divisionPlayers[i-1].seasonal_points) {
        rank = i + 1;
      }
      if (divisionPlayers[i].player_id === player.player_id) {
        return rank;
      }
    }
    
    return divisionPlayers.length + 1;
  };

  // Get CSS class for divisional leaders
  const getLeaderClass = (player: Player): string => {
    if (player.seasonal_points === 0) return '';
    const rank = getDivisionalRank(player);
    if (rank === 1) return 'division-leader-1st';
    if (rank === 2) return 'division-leader-2nd';
    if (rank === 3) return 'division-leader-3rd';
    return '';
  };

  // Get rank info: numeric rank, a short label, and a decorative emoji.
  type RankInfo = { emoji: string; label: string } | null;
  const getRankInfo = (player: Player): RankInfo => {
    if (player.seasonal_points === 0) return null;
    const rank = getDivisionalRank(player);
    if (rank === 1) return { emoji: '👑', label: `1st in ${player.division}` };
    if (rank === 2) return { emoji: '🥈', label: `2nd in ${player.division}` };
    if (rank === 3) return { emoji: '🥉', label: `3rd in ${player.division}` };
    return null;
  };

  return (
    <div className="player-list-view">
      <div className="table-container">
        <table
          className="players-table"
          aria-label="Players sorted alphabetically by name. Activate a player to view their details."
        >
          <thead>
            <tr>
              <th scope="col">Name</th>
              <th scope="col" className="division-header">
                <label htmlFor="division-filter">Division</label>
                <select
                  id="division-filter"
                  value={divisionFilter}
                  onChange={(e) => setDivisionFilter(e.target.value)}
                  className="division-filter"
                  aria-label="Filter players by division"
                >
                  <option value="All">(All)</option>
                  <option value="Pro">Pro</option>
                  <option value="Am">Am</option>
                  <option value="Junior">Junior</option>
                </select>
              </th>
              {onEditPlayer && (
                <th scope="col" className="actions-header">Actions</th>
              )}
            </tr>
          </thead>
          <tbody>
            {sortedPlayers.map(player => {
              const rankInfo = getRankInfo(player);
              return (
                <tr
                  key={player.player_id}
                  className={getLeaderClass(player)}
                >
                  <td>
                    <button
                      type="button"
                      className="player-row-button"
                      onClick={() => onPlayerClick(player)}
                    >
                      <span className="player-name">
                        {rankInfo && (
                          <span className="rank-display">
                            <span aria-hidden="true">{rankInfo.emoji}</span>
                            <span className="sr-only">{rankInfo.label}. </span>
                          </span>
                        )}
                        <span className="player-name-text">{player.player_name}</span>
                        {player.nickname && (
                          <span className="nickname">"{player.nickname}"</span>
                        )}
                      </span>
                    </button>
                  </td>
                  <td>
                    <button
                      type="button"
                      className="player-division-button"
                      onClick={() => onPlayerClick(player)}
                      tabIndex={-1}
                      aria-hidden="true"
                    >
                      {player.division}
                    </button>
                  </td>
                  {onEditPlayer && (
                    <td className="actions-cell">
                      <button
                        className="edit-button-small"
                        onClick={(e) => {
                          e.stopPropagation();
                          onEditPlayer(player);
                        }}
                        aria-label={`Edit ${player.player_name}`}
                      >
                        <span aria-hidden="true">✏️</span>
                      </button>
                    </td>
                  )}
                </tr>
              );
            })}
          </tbody>
        </table>
        {sortedPlayers.length === 0 && (
          <div className="empty-state">No players found.</div>
        )}
      </div>
    </div>
  );
};

export default PlayerList;
