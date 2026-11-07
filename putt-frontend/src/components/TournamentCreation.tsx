import React, { useState, useEffect } from 'react';
import { API_BASE_URL } from '../config/api';
import { Player } from '../types/player';
import { loadPayoutDefaults } from './Admin';

interface TournamentCreationProps {
  onBack: () => void;
  onTournamentCreated: () => void;
  existingPendingId?: number | null;
}

interface SelectedPlayer extends Player {
  bought_ace_pot: boolean;
}

const FACTORY_DEFAULTS = { ace_pot_per_player: 1.00 };
const DEFAULTS_KEY = 'dgputt_tournament_defaults';

function loadDefaults() {
  try {
    const saved = localStorage.getItem(DEFAULTS_KEY);
    return saved ? { ...FACTORY_DEFAULTS, ...JSON.parse(saved) } : { ...FACTORY_DEFAULTS };
  } catch {
    return { ...FACTORY_DEFAULTS };
  }
}

const TournamentCreation: React.FC<TournamentCreationProps> = ({ onBack, onTournamentCreated, existingPendingId = null }) => {
  const [availablePlayers, setAvailablePlayers] = useState<Player[]>([]);
  const [selectedPlayers, setSelectedPlayers] = useState<SelectedPlayer[]>([]);
  const [pendingTournamentId, setPendingTournamentId] = useState<number | null>(existingPendingId);
  const [tournamentDate, setTournamentDate] = useState(() => {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  });
  const [stations, setStations] = useState(4);
  const [acePotPerPlayer, setAcePotPerPlayer] = useState<number>(() => loadDefaults().ace_pot_per_player);
  const [payoutConfig, setPayoutConfig] = useState(() => loadPayoutDefaults());
  const [payoutWarning, setPayoutWarning] = useState<string | null>(null);
  const [showPayoutForm, setShowPayoutForm] = useState(false);
  const [warningShake, setWarningShake] = useState(false);
  const [loading, setLoading] = useState(false);
  const [showNewPlayerForm, setShowNewPlayerForm] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [newPlayer, setNewPlayer] = useState({
    player_name: '',
    nickname: '',
    division: 'Am' as 'Pro' | 'Am' | 'Junior'
  });

  const initializingRef = React.useRef(false);

  useEffect(() => {
    fetchPlayers();
    if (existingPendingId) {
      loadExistingPending(existingPendingId);
    } else {
      initPendingTournament();
    }
  }, []);


  const loadExistingPending = async (id: number) => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/putt/tournaments?id=${id}`, { credentials: 'include' });
      if (res.ok) {
        const data = await res.json();
        setSelectedPlayers((data.registered_players || []).map((p: any) => ({ ...p, bought_ace_pot: p.bought_ace_pot ?? false })));
      }
    } catch (error) {
      console.error('Failed to load existing pending tournament:', error);
    }
  };

  const initPendingTournament = async () => {
    if (initializingRef.current) return;
    initializingRef.current = true;
    try {
      const res = await fetch(`${API_BASE_URL}/api/putt/tournaments/pending`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          tournament_date: tournamentDate,
          stations,
          buy_in_per_player: payoutConfig.buy_in_per_player,
          ace_pot_per_player: acePotPerPlayer,
          payout_config: { mode: payoutConfig.mode, second_place_value: payoutConfig.second_place_value }
        })
      });
      if (res.ok) {
        const data = await res.json();
        setPendingTournamentId(data.tournament_id);
      }
    } catch (error) {
      console.error('Failed to create pending tournament:', error);
    }
  };

  const fetchPlayers = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/putt/players`, { credentials: 'include' });
      if (response.ok) {
        const data = await response.json();
        setAvailablePlayers(data);
      }
    } catch (error) {
      console.error('Failed to fetch players:', error);
    }
  };

  const filteredPlayers = availablePlayers.filter(player =>
    !selectedPlayers.find(p => p.player_id === player.player_id) &&
    (player.player_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (player.nickname && player.nickname.toLowerCase().includes(searchTerm.toLowerCase())))
  ).sort((a, b) => a.player_name.localeCompare(b.player_name));

  const addPlayer = async (player: Player) => {
    if (selectedPlayers.find(p => p.player_id === player.player_id)) return;
    if (!pendingTournamentId) { alert('Tournament not initialized yet. Please wait a moment.'); return; }

    try {
      const res = await fetch(`${API_BASE_URL}/api/putt/tournaments/${pendingTournamentId}/players`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ player_id: player.player_id, bought_ace_pot: false, ace_pot_per_player: acePotPerPlayer })
      });
      if (res.ok) {
        setSelectedPlayers(prev => [...prev, { ...player, bought_ace_pot: false }]);
      }
    } catch (error) {
      console.error('Failed to add player:', error);
    }
  };

  const removePlayer = async (playerId: number) => {
    if (pendingTournamentId) {
      await fetch(`${API_BASE_URL}/api/putt/tournaments/${pendingTournamentId}/players/${playerId}`, {
        method: 'DELETE',
        credentials: 'include'
      }).catch(() => {});
    }
    setSelectedPlayers(prev => prev.filter(p => p.player_id !== playerId));
  };

  const toggleAcePot = async (playerId: number) => {
    const player = selectedPlayers.find(p => p.player_id === playerId);
    if (!player || !pendingTournamentId) return;

    const newVal = !player.bought_ace_pot;
    // Remove and re-add with updated ace pot flag
    await fetch(`${API_BASE_URL}/api/putt/tournaments/${pendingTournamentId}/players/${playerId}`, {
      method: 'DELETE', credentials: 'include'
    }).catch(() => {});
    await fetch(`${API_BASE_URL}/api/putt/tournaments/${pendingTournamentId}/players`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ player_id: playerId, bought_ace_pot: newVal, ace_pot_per_player: acePotPerPlayer })
    }).catch(() => {});

    setSelectedPlayers(prev => prev.map(p =>
      p.player_id === playerId ? { ...p, bought_ace_pot: newVal } : p
    ));
  };

  const saveAsDefault = () => {
    localStorage.setItem(DEFAULTS_KEY, JSON.stringify({ ace_pot_per_player: acePotPerPlayer }));
    alert('Saved as new default.');
  };

  const resetToFactoryDefault = () => {
    localStorage.removeItem(DEFAULTS_KEY);
    setAcePotPerPlayer(FACTORY_DEFAULTS.ace_pot_per_player);
  };

  const handleNewPlayerSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const duplicate = availablePlayers.find(p =>
      p.player_name.toLowerCase() === newPlayer.player_name.toLowerCase()
    );
    if (duplicate) { alert('Player already exists in the league'); return; }

    try {
      const response = await fetch(`${API_BASE_URL}/api/putt/players`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(newPlayer)
      });
      if (response.ok) {
        const result = await response.json();
        const createdPlayer = result.created[0];
        setAvailablePlayers(prev => [...prev, createdPlayer]);
        await addPlayer(createdPlayer);
        setNewPlayer({ player_name: '', nickname: '', division: 'Am' });
        setShowNewPlayerForm(false);
      } else {
        const error = await response.json();
        alert(`Error creating player: ${error.errors ? error.errors.join('\n') : error.error}`);
      }
    } catch (error) {
      console.error('Failed to create player:', error);
    }
  };

  const createTournament = async () => {
    if (selectedPlayers.length < 2) {
      alert('Need at least 2 players to create a tournament');
      return;
    }
    const warning = validatePayout(selectedPlayers.length);
    if (warning) {
      setShowPayoutForm(false);
      setPayoutWarning(warning);
      return;
    }
    await submitTournament();
  };

  const computePayoutSplit = (playerCount: number) => {
    const pot = payoutConfig.buy_in_per_player * playerCount;
    let second = payoutConfig.mode === 'fixed'
      ? payoutConfig.second_place_value
      : pot * (payoutConfig.second_place_value / 100);
    let first = pot - second;
    if (first < second) { [first, second] = [second, first]; }
    return { pot, first, second };
  };

  const validatePayout = (playerCount: number): string | null => {
    const { pot, first, second } = computePayoutSplit(playerCount);
    if (payoutConfig.mode === 'percentage' && payoutConfig.second_place_value > 100) {
      return `2nd place percentage (${payoutConfig.second_place_value}%) exceeds 100%. Please go to Admin → Season Management to fix this before creating a tournament.`;
    }
    if (payoutConfig.mode === 'fixed' && payoutConfig.second_place_value >= pot) {
      return `With ${playerCount} players the total pot is $${pot.toFixed(2)}, but the 2nd place fixed amount is $${payoutConfig.second_place_value.toFixed(2)}. 1st place will receive $${first.toFixed(2)} and 2nd place will receive $${second.toFixed(2)}. Proceed or go to Admin → Season Management to adjust.`;
    }
    return null;
  };

  const submitTournament = async () => {
    if (!pendingTournamentId) { alert('No pending tournament found.'); return; }
    setPayoutWarning(null);
    setLoading(true);
    try {
      const finalizeRes = await fetch(`${API_BASE_URL}/api/putt/tournaments/${pendingTournamentId}/finalize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ ace_pot_per_player: acePotPerPlayer })
      });

      if (!finalizeRes.ok) {
        const err = await finalizeRes.json();
        alert(`Failed to finalize tournament: ${err.error || 'Unknown error'}`);
        return;
      }

      const matchesResponse = await fetch(`${API_BASE_URL}/api/putt/tournaments/${pendingTournamentId}/generate-matches`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ stations })
      });

      if (matchesResponse.ok) {
        setPendingTournamentId(null);
        onTournamentCreated();
      } else {
        await fetch(`${API_BASE_URL}/api/putt/tournaments/${pendingTournamentId}`, {
          method: 'DELETE', credentials: 'include'
        });
        setPendingTournamentId(null);
        const matchError = await matchesResponse.json();
        alert(`Failed to generate matches: ${matchError.error || 'Unknown error'}. Tournament has been deleted.`);
      }
    } catch (error) {
      console.error('Failed to create tournament:', error);
      alert('Network error: Failed to create tournament. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const acePotCount = selectedPlayers.filter(p => p.bought_ace_pot).length;
  const isCustomDefault = JSON.stringify(loadDefaults()) !== JSON.stringify(FACTORY_DEFAULTS);

  return (
    <div className="tournament-creation">
      <div className="back-button-container">
        <button className="back-button" onClick={onBack}>← Back</button>
      </div>

      <div className="page-header">
        <h2>Create Tournament</h2>
      </div>

      {payoutWarning && (
        <div className="payout-warning-modal">
          <div className="payout-warning-content">
            <h3>Payout Configuration Notice</h3>
            <p className={warningShake ? 'shake' : ''}>{payoutWarning}</p>
            {showPayoutForm ? (
              <>
                <div className="payout-modal-settings">
                  <div className="payout-modal-row">
                    <label>Buy-in per Player ($):</label>
                    <input
                      type="number" min="0" step="0.25"
                      value={payoutConfig.buy_in_per_player}
                      onChange={(e) => setPayoutConfig({ ...payoutConfig, buy_in_per_player: parseFloat(e.target.value) || 0 })}
                    />
                  </div>
                  <div className="payout-modal-row">
                    <label>Mode:</label>
                    <div className="mode-toggle">
                      <button type="button" className={payoutConfig.mode === 'fixed' ? 'active' : ''} onClick={() => setPayoutConfig({ ...payoutConfig, mode: 'fixed' })}>Fixed ($)</button>
                      <button type="button" className={payoutConfig.mode === 'percentage' ? 'active' : ''} onClick={() => setPayoutConfig({ ...payoutConfig, mode: 'percentage' })}>Percentage (%)</button>
                    </div>
                  </div>
                  <div className="payout-modal-row">
                    <label>2nd Place ({payoutConfig.mode === 'fixed' ? '$' : '%'}):</label>
                    <input
                      type="number" min="0" step="1"
                      max={payoutConfig.mode === 'percentage' ? 100 : undefined}
                      value={payoutConfig.second_place_value}
                      onChange={(e) => setPayoutConfig({ ...payoutConfig, second_place_value: parseFloat(e.target.value) || 0 })}
                    />
                  </div>
                </div>
                <div className="form-buttons">
                  <button onClick={() => {
                    const w = validatePayout(selectedPlayers.length);
                    if (w) {
                      setPayoutWarning(w);
                      setShowPayoutForm(false);
                      setWarningShake(true);
                      setTimeout(() => setWarningShake(false), 600);
                    } else {
                      submitTournament();
                    }
                  }}>Apply & Create</button>
                  <button onClick={() => setShowPayoutForm(false)}>Cancel Edit</button>
                </div>
              </>
            ) : (
              <div className="form-buttons">
                <button onClick={() => setShowPayoutForm(true)}>Edit Payout Settings</button>
                <button onClick={submitTournament}>Proceed Anyway</button>
                <button onClick={() => setPayoutWarning(null)}>Cancel</button>
              </div>
            )}
          </div>
        </div>
      )}

      <div className="creation-form">
        <div className="form-section parent">
          <div>
            <label>Tournament Date:</label>
            <input
              type="date"
              value={tournamentDate}
              onChange={(e) => setTournamentDate(e.target.value)}
            />
          </div><div>
            <label>Number of Stations:</label>
            <input
              type="number"
              min="1"
              max="20"
              value={stations}
              onChange={(e) => setStations(parseInt(e.target.value))}
            />
          </div><div>
            <label>Ace Pot Buy-in per Player ($):</label>
            <input
              type="number"
              min="0"
              step="0.25"
              value={acePotPerPlayer}
              onChange={(e) => setAcePotPerPlayer(parseFloat(e.target.value) || 0)}
            />
            <div className="default-actions">
            <button type="button" className="save-default-button" onClick={saveAsDefault}>
              Save as Default
            </button>
            {isCustomDefault && (
              <button type="button" className="reset-default-button" onClick={resetToFactoryDefault}>
                Reset to Original Default
              </button>
            )}
          </div>
          </div>
          
        </div>

        <div className="players-section">
          <div className="available-players">
            <h3>Available Players</h3>
            <input
              type="text"
              placeholder="Search players..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="search-input"
            />
            <div className="player-list">
              {filteredPlayers.map(player => (
                <div key={player.player_id} className="player-item">
                  <span>{player.player_name} ({player.division})</span>
                  <button onClick={() => addPlayer(player)}>Add</button>
                </div>
              ))}
            </div>
            <button 
              className="new-player-button"
              onClick={() => setShowNewPlayerForm(true)}
            >
              Register New Player
            </button>
          </div>

          <div className="selected-players">
            <h3>Tournament Players ({selectedPlayers.length})</h3>
            <div className="ace-pot-summary">
              Ace Pot Buy-ins: {acePotCount} (${(acePotCount * acePotPerPlayer).toFixed(2)})
            </div>
            <div className="player-list">
              {selectedPlayers.map(player => (
                <div key={player.player_id} className="player-item selected">
                  <span>{player.player_name} ({player.division})</span>
                  <div className="player-controls">
                    <label className="ace-pot-checkbox">
                      <input
                        type="checkbox"
                        checked={player.bought_ace_pot}
                        onChange={() => toggleAcePot(player.player_id)}
                      />
                      Ace Pot
                    </label>
                    <button onClick={() => removePlayer(player.player_id)}>Remove</button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {showNewPlayerForm && (
          <div className="new-player-form">
            <h3>Register New Player</h3>
            <form onSubmit={handleNewPlayerSubmit}>
              <input
                type="text"
                placeholder="Player Name"
                value={newPlayer.player_name}
                onChange={(e) => setNewPlayer({...newPlayer, player_name: e.target.value})}
                required
              />
              <input
                type="text"
                placeholder="Nickname (optional)"
                value={newPlayer.nickname}
                onChange={(e) => setNewPlayer({...newPlayer, nickname: e.target.value})}
              />
              <select
                value={newPlayer.division}
                onChange={(e) => setNewPlayer({...newPlayer, division: e.target.value as 'Pro' | 'Am' | 'Junior'})}
              >
                <option value="Pro">Pro</option>
                <option value="Am">Am</option>
                <option value="Junior">Junior</option>
              </select>
              <div className="form-buttons">
                <button type="submit">Add Player</button>
                <button type="button" onClick={() => setShowNewPlayerForm(false)}>Cancel</button>
              </div>
            </form>
          </div>
        )}

        <div className="create-section">
          <button 
            className="create-tournament-button"
            onClick={createTournament}
            disabled={loading || selectedPlayers.length < 2}
          >
            {loading ? 'Creating...' : 'Create Tournament'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default TournamentCreation;

