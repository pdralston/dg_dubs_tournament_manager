import React, { useState, useEffect } from 'react';
import { API_BASE_URL } from '../config/api';
import { Player } from '../types';

interface PlayerListProps {
  userRole: string;
  onPlayerSelect: (name: string) => void;
}

const PlayerList: React.FC<PlayerListProps> = ({ userRole, onPlayerSelect }) => {
  const [players, setPlayers] = useState<Player[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  const [newName, setNewName] = useState('');
  const [newRating, setNewRating] = useState('1000');
  const [error, setError] = useState('');

  const canEdit = userRole === 'admin' || userRole === 'director';

  const fetchPlayers = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/players`, { credentials: 'include' });
      if (res.ok) setPlayers(await res.json());
    } catch {
      setError('Failed to load players');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchPlayers(); }, []);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    try {
      const res = await fetch(`${API_BASE_URL}/api/players`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ name: newName, rating: parseFloat(newRating) })
      });
      if (res.ok) {
        setNewName('');
        setNewRating('1000');
        setShowAddForm(false);
        fetchPlayers();
      } else {
        const data = await res.json();
        setError(data.error || 'Failed to add player');
      }
    } catch {
      setError('Network error');
    }
  };

  if (loading) return <div className="loading">Loading players...</div>;

  return (
    <div className="page-content">
      <div className="page-header">
        <h2>Players</h2>
        {canEdit && (
          <button className="action-button" onClick={() => setShowAddForm(!showAddForm)}>
            {showAddForm ? 'Cancel' : '+ Add Player'}
          </button>
        )}
      </div>

      {error && <div className="error-message" role="alert">{error}</div>}

      {showAddForm && (
        <form className="inline-form" onSubmit={handleAdd}>
          <div className="form-group">
            <label htmlFor="player-name">Name:</label>
            <input id="player-name" value={newName} onChange={e => setNewName(e.target.value)} required />
          </div>
          <div className="form-group">
            <label htmlFor="player-rating">Rating:</label>
            <input id="player-rating" type="number" value={newRating} onChange={e => setNewRating(e.target.value)} />
          </div>
          <button type="submit" className="action-button">Add</button>
        </form>
      )}

      <table className="data-table">
        <thead>
          <tr>
            <th>Rank</th>
            <th>Name</th>
            <th>Rating</th>
          </tr>
        </thead>
        <tbody>
          {players.map((p, i) => (
            <tr key={p.name} onClick={() => onPlayerSelect(p.name)} className="clickable-row">
              <td>{i + 1}</td>
              <td>{p.name}</td>
              <td>{Math.round(p.rating)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default PlayerList;
