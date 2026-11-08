import React, { useState, useEffect } from 'react';
import PlayerRegistration from './PlayerRegistration';
import PlayerList from './PlayerList';
import { Player } from '../types/player';
import { API_BASE_URL } from '../config/api';
import { getTeamDisplayName } from '../utils/teamUtils';

interface PlayerManagerProps {
  userRole?: string;
  initialPlayerId?: number | null;
}

const TournamentHistoryBySeason: React.FC<{
  history: any[];
  onTournamentClick: (t: any) => void;
}> = ({ history, onTournamentClick }) => {
  const seasons: Record<string, any[]> = {};
  history.forEach(t => {
    const key = t.season_name || 'Current Season';
    if (!seasons[key]) seasons[key] = [];
    seasons[key].push(t);
  });

  // Always put Current Season first, even if empty
  const seasonKeys = [
    'Current Season',
    ...Object.keys(seasons).filter(k => k !== 'Current Season')
  ];

  const [selected, setSelected] = useState<string>('Current Season');
  const activeKey = seasons[selected] ? selected : seasonKeys[0] || 'Current Season';

  return (
    <div className="tournament-history">
      <label htmlFor="season-history-select" className="sr-only">Select season</label>
      <select id="season-history-select" value={activeKey} onChange={e => setSelected(e.target.value)} className="season-select">
        {seasonKeys.map(k => <option key={k} value={k}>{k}</option>)}
      </select>
      {(seasons[activeKey] || []).length === 0 ? (
        <p className="detail-empty">No tournaments this season.</p>
      ) : (
        <div className="detail-table-card">
          <table className="detail-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Status</th>
                <th>Place</th>
                <th>Points</th>
                <th><span className="sr-only">Ace Pot</span></th>
              </tr>
            </thead>
            <tbody>
              {(seasons[activeKey] || []).map((t: any) => (
                <tr
                  key={t.tournament_id}
                  className="clickable-row"
                  onClick={() => onTournamentClick(t)}
                  role="button"
                  tabIndex={0}
                  aria-label={`View standings for tournament on ${t.tournament_date}`}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      onTournamentClick(t);
                    }
                  }}
                >
                  <td>{t.tournament_date}</td>
                  <td>{t.status}</td>
                  <td>{t.final_place ?? '—'}</td>
                  <td>{t.points_earned}</td>
                  <td>
                    {t.won_ace_pot === true && (
                      <span className="ace-winner"><span aria-hidden="true">🎯 </span>ACE POT</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

const PlayerManager: React.FC<PlayerManagerProps> = ({ userRole = 'Viewer', initialPlayerId = null }) => {
  const [players, setPlayers] = useState<Player[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  const [selectedPlayer, setSelectedPlayer] = useState<Player | null>(null);
  const [playerDetail, setPlayerDetail] = useState<any>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [showBulkRegister, setShowBulkRegister] = useState(false);
  const [csvData, setCsvData] = useState('');
  const [bulkLoading, setBulkLoading] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [editingPlayer, setEditingPlayer] = useState<Player | null>(null);
  const [editForm, setEditForm] = useState({ player_name: '', nickname: '', division: '' });
  // Tournament standings modal (opened from the tournament-history table)
  const [standingsTournament, setStandingsTournament] = useState<any | null>(null);
  const [standingsTeams, setStandingsTeams] = useState<any[] | null>(null);
  const [standingsLoading, setStandingsLoading] = useState(false);

  const openStandings = async (t: any) => {
    setStandingsTournament(t);
    setStandingsTeams(null);
    setStandingsLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/putt/tournaments/${t.tournament_id}/teams`, { credentials: 'include' });
      if (res.ok) {
        const teams = await res.json();
        setStandingsTeams(teams);
      } else {
        setStandingsTeams([]);
      }
    } catch (error) {
      console.error('Failed to load standings:', error);
      setStandingsTeams([]);
    } finally {
      setStandingsLoading(false);
    }
  };

  const closeStandings = () => {
    setStandingsTournament(null);
    setStandingsTeams(null);
  };

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

  const getDivisionalRankSuffix = (player: Player): string => {
    const rank = getDivisionalRank(player);
    if (rank === 1) return '1st';
    if (rank === 2) return '2nd';
    if (rank === 3) return '3rd';
    return '';
  };

  useEffect(() => {
    fetchPlayers();
    if (initialPlayerId) {
      setLoadingDetail(true);
      setSelectedPlayer({ player_id: initialPlayerId, player_name: '', nickname: undefined, division: 'Am', seasonal_points: 0, seasonal_cash: 0 });
      fetch(`${API_BASE_URL}/api/putt/players/${initialPlayerId}`, { credentials: 'include' })
        .then(r => r.json())
        .then(detail => {
          setSelectedPlayer({ player_id: detail.player_id, player_name: detail.player_name, nickname: detail.nickname, division: detail.division, seasonal_points: detail.seasonal_points, seasonal_cash: detail.seasonal_cash });
          setPlayerDetail(detail);
          setLoadingDetail(false);
        });
    }
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

  const handleEditPlayer = (player: Player) => {
    setEditingPlayer(player);
    setEditForm({
      player_name: player.player_name,
      nickname: player.nickname || '',
      division: player.division
    });
  };

  const handleUpdatePlayer = async () => {
    if (!editingPlayer) return;
    
    try {
      const response = await fetch(`${API_BASE_URL}/api/putt/players/${editingPlayer.player_id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(editForm)
      });
      
      if (response.ok) {
        await fetchPlayers();
        setEditingPlayer(null);
        setEditForm({ player_name: '', nickname: '', division: '' });
      }
    } catch (error) {
      console.error('Failed to update player:', error);
    }
  };

  const filteredPlayers = players.filter(player =>
    player.player_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (player.nickname && player.nickname.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  const handlePlayerClick = async (player: Player) => {
    setSelectedPlayer(player);
    setLoadingDetail(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/putt/players/${player.player_id}`, { 
        method: 'GET',
        credentials: 'include'
      });
      if (response.ok) {
        const data = await response.json();
        setPlayerDetail(data);
      }
    } catch (error) {
      console.error('Failed to fetch player details:', error);
    } finally {
      setLoadingDetail(false);
    }
  };

  const handlePlayerAdded = (newPlayer: Player) => {
    setPlayers(prev => [...prev, newPlayer]);
    setShowAddForm(false);
  };

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      setSelectedFile(file);
      const reader = new FileReader();
      reader.onload = (e) => {
        setCsvData(e.target?.result as string);
      };
      reader.readAsText(file);
    }
  };

  const handleBulkRegister = async () => {
    if (!csvData.trim()) return;
    
    setBulkLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/putt/players/batch-csv`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ csv_data: csvData })
      });
      
      if (response.ok) {
        const result = await response.json();
        setPlayers(prev => [...prev, ...result.created]);
        setShowBulkRegister(false);
        setCsvData('');
        setSelectedFile(null);
        if (result.errors?.length > 0) {
          alert(`Registered ${result.created.length} players. Errors: ${result.errors.join(', ')}`);
        }
      }
    } catch (error) {
      console.error('Bulk registration failed:', error);
    } finally {
      setBulkLoading(false);
    }
  };

  if (loading) return <div className="loading">Loading players...</div>;

  if (selectedPlayer) {
    return (
      <div className="player-manager">
        <div className="back-button-container back-button-container--inline">
          <button className="back-button" onClick={() => {setSelectedPlayer(null); setPlayerDetail(null);}}>
            ← Back to Players
          </button>
        </div>
        <div className={`player-detail ${selectedPlayer.seasonal_points > 0 && getDivisionalRank(selectedPlayer) <= 3 ? `division-leader-${getDivisionalRankSuffix(selectedPlayer)}` : ''}`}>
          <h2>
            {selectedPlayer.seasonal_points > 0 && getDivisionalRank(selectedPlayer) === 1 && (
              <>
                <span aria-hidden="true">👑 </span>
                <span className="sr-only">1st in {selectedPlayer.division}. </span>
              </>
            )}
            {selectedPlayer.seasonal_points > 0 && getDivisionalRank(selectedPlayer) === 2 && (
              <>
                <span aria-hidden="true">🥈 </span>
                <span className="sr-only">2nd in {selectedPlayer.division}. </span>
              </>
            )}
            {selectedPlayer.seasonal_points > 0 && getDivisionalRank(selectedPlayer) === 3 && (
              <>
                <span aria-hidden="true">🥉 </span>
                <span className="sr-only">3rd in {selectedPlayer.division}. </span>
              </>
            )}
            {selectedPlayer.player_name}
          </h2>
          {selectedPlayer.nickname && <p className="nickname">"{selectedPlayer.nickname}"</p>}
          <div className="player-stats">
            <div className="stat">
              <label>Division:</label>
              <span>{selectedPlayer.division}</span>
            </div>
            <div className="stat">
              <label>Seasonal Points:</label>
              <span>{selectedPlayer.seasonal_points}</span>
            </div>
            <div className="stat">
              <label>Seasonal Cash:</label>
              <span>${selectedPlayer.seasonal_cash}</span>
            </div>
            {playerDetail && (
              <>
                <div className="stat">
                  <label>Lifetime Earnings:</label>
                  <span>${(playerDetail.lifetime_earnings + parseFloat(selectedPlayer.seasonal_cash as any)).toFixed(2)}</span>
                </div>
                <div className="stat">
                  <label>Lifetime Ace Pots:</label>
                  <span>{playerDetail.lifetime_ace_pots}</span>
                </div>
                <div className="stat">
                  <label>Events Participated:</label>
                  <span>{playerDetail.events_participated + playerDetail.tournament_history.filter((t: any) => t.season_name === null).length}</span>
                </div>
                <div className="stat">
                  <label>Seasonal Wins:</label>
                  <span>{playerDetail.seasonal_wins}</span>
                </div>
                <div className="stat">
                  <label>Lifetime Wins:</label>
                  <span>{playerDetail.lifetime_wins}</span>
                </div>
                {playerDetail.average_place !== null && (
                  <div className="stat">
                    <label>Average Place:</label>
                    <span>{Number(playerDetail.average_place).toFixed(2)}</span>
                  </div>
                )}
              </>
            )}
          </div>
        </div>

        {loadingDetail ? (
          <div className="loading">Loading tournament history...</div>
        ) : playerDetail && (
          <>
            <section className="detail-section">
              <h3 className="detail-section-title">Tournament History</h3>
              <TournamentHistoryBySeason history={playerDetail.tournament_history} onTournamentClick={openStandings} />
            </section>

            <section className="detail-section">
              <h3 className="detail-section-title">Teammate History</h3>
              {playerDetail.teammate_history.length > 0 ? (
                <div className="detail-table-card">
                  <table className="detail-table">
                    <thead>
                      <tr>
                        <th>Teammate</th>
                        <th>Times Paired</th>
                        <th>Avg Place</th>
                      </tr>
                    </thead>
                    <tbody>
                      {playerDetail.teammate_history.map((tm: any) => (
                        <tr key={tm.teammate_id}>
                          <td className="teammate-name">
                            {tm.teammate_name}
                            {tm.teammate_nickname && (
                              <span className="nickname"> "{tm.teammate_nickname}"</span>
                            )}
                          </td>
                          <td>{tm.times_paired}</td>
                          <td>{tm.average_place ?? '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="detail-empty">No teammate history</p>
              )}
            </section>
          </>
        )}

        {standingsTournament && (
          <div
            className="edit-modal-overlay"
            role="presentation"
            onClick={closeStandings}
          >
            <div
              className="standings-modal"
              role="dialog"
              aria-modal="true"
              aria-labelledby="standings-title"
              onClick={(e) => e.stopPropagation()}
            >
              <h3 id="standings-title">Final Standings — {standingsTournament.tournament_date}</h3>
              {standingsLoading ? (
                <p className="detail-empty">Loading standings…</p>
              ) : standingsTeams && standingsTeams.length > 0 ? (
                <div className="detail-table-card">
                  <table className="detail-table">
                    <thead>
                      <tr>
                        <th>Place</th>
                        <th>Team</th>
                      </tr>
                    </thead>
                    <tbody>
                      {[...standingsTeams]
                        .sort((a, b) => (a.final_place ?? 999) - (b.final_place ?? 999))
                        .map((team: any) => (
                          <tr key={team.team_id}>
                            <td>{team.final_place ?? '—'}</td>
                            <td>{getTeamDisplayName(team)}</td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="detail-empty">No standings available for this tournament.</p>
              )}
              <div className="modal-buttons">
                <button onClick={closeStandings}>Close</button>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="player-manager">
      <div className="page-header">
        <h2>Players</h2>
        {(userRole === 'Admin' || userRole === 'Director') && (
          <div className="header-buttons">
            <button 
              className="add-button"
              onClick={() => setShowAddForm(!showAddForm)}
            >
              {showAddForm ? 'Cancel' : 'Add Player'}
            </button>
            <button 
              className="add-button"
              onClick={() => setShowBulkRegister(!showBulkRegister)}
            >
              Add Players
            </button>
          </div>
        )}
      </div>
      
      {showAddForm && (
        <PlayerRegistration onPlayerAdded={handlePlayerAdded} />
      )}
      
      {showBulkRegister && (
        <div
          className="bulk-register-modal"
          role="region"
          aria-labelledby="bulk-register-title"
        >
          <h3 id="bulk-register-title">Bulk Register Players</h3>
          <label htmlFor="bulk-csv-file">
            Select a CSV file with headers: player_name,nickname,division
          </label>
          <input
            id="bulk-csv-file"
            type="file"
            accept=".csv"
            onChange={handleFileSelect}
            style={{ marginBottom: '10px', display: 'block' }}
          />
          {selectedFile && (
            <p>Selected: {selectedFile.name}</p>
          )}
          {csvData && (
            <div>
              <h4>Preview:</h4>
              <pre style={{ background: '#f8f9fa', color: '#14172C', padding: '10px', fontSize: '12px', maxHeight: '200px', overflow: 'auto' }}>
                {csvData.split('\n').slice(0, 5).join('\n')}
                {csvData.split('\n').length > 5 && '\n...'}
              </pre>
            </div>
          )}
          <div>
            <button onClick={handleBulkRegister} disabled={bulkLoading || !csvData}>
              {bulkLoading ? 'Registering...' : 'Register Players'}
            </button>
            <button onClick={() => {setShowBulkRegister(false); setCsvData(''); setSelectedFile(null);}}>Cancel</button>
          </div>
        </div>
      )}
      
      <div className="search-section">
        <label htmlFor="player-search" className="sr-only">Search players</label>
        <input
          id="player-search"
          type="text"
          placeholder="Search players..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="search-input"
        />
      </div>
      
      <PlayerList 
        players={players}
        searchTerm={searchTerm}
        onPlayerClick={handlePlayerClick}
        onEditPlayer={(userRole === 'Admin' || userRole === 'Director') ? handleEditPlayer : undefined}
      />
      
      {editingPlayer && (
        <div
          className="edit-modal-overlay"
          role="presentation"
          onClick={() => setEditingPlayer(null)}
        >
          <div
            className="edit-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="edit-player-title"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 id="edit-player-title">Edit Player</h3>
            <div className="form-group">
              <label htmlFor="edit-player-name">Player Name:</label>
              <input
                id="edit-player-name"
                type="text"
                value={editForm.player_name}
                onChange={(e) => setEditForm({...editForm, player_name: e.target.value})}
              />
            </div>
            <div className="form-group">
              <label htmlFor="edit-player-nickname">Nickname:</label>
              <input
                id="edit-player-nickname"
                type="text"
                value={editForm.nickname}
                onChange={(e) => setEditForm({...editForm, nickname: e.target.value})}
              />
            </div>
            <div className="form-group">
              <label htmlFor="edit-player-division">Division:</label>
              <select
                id="edit-player-division"
                value={editForm.division}
                onChange={(e) => setEditForm({...editForm, division: e.target.value})}
              >
                <option value="Am">Am</option>
                <option value="Pro">Pro</option>
                <option value="Junior">Junior</option>
              </select>
            </div>
            <div className="modal-buttons">
              <button onClick={() => setEditingPlayer(null)}>Cancel</button>
              <button onClick={handleUpdatePlayer}>Update</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default PlayerManager;
