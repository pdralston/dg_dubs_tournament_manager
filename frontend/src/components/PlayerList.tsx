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
  const [searchTerm, setSearchTerm] = useState('');
  const [editingPlayer, setEditingPlayer] = useState<string | null>(null);
  const [editName, setEditName] = useState('');
  const [renameError, setRenameError] = useState('');

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

  const handleRename = async (originalName: string) => {
    const trimmed = editName.trim();
    if (!trimmed || trimmed === originalName) {
      setEditingPlayer(null);
      setRenameError('');
      return;
    }
    setRenameError('');
    try {
      const res = await fetch(`${API_BASE_URL}/api/players/${encodeURIComponent(originalName)}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ new_name: trimmed }),
      });
      if (res.ok) {
        setEditingPlayer(null);
        setRenameError('');
        fetchPlayers();
      } else {
        const data = await res.json();
        setRenameError(data.error || 'Failed to rename player');
      }
    } catch {
      setRenameError('Network error');
    }
  };

  const startEditing = (playerName: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setEditingPlayer(playerName);
    setEditName(playerName);
    setRenameError('');
  };

  const cancelEditing = () => {
    setEditingPlayer(null);
    setRenameError('');
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
      {renameError && <div className="error-message" role="alert">{renameError}</div>}

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

      <input type="text" placeholder="Search players..." value={searchTerm} onChange={e => setSearchTerm(e.target.value)} className="search-input" aria-label="Search players" />

      <table className="data-table">
        <thead>
          <tr>
            <th>Rank</th>
            <th>Name</th>
            <th>Rating</th>
            {canEdit && <th>Actions</th>}
          </tr>
        </thead>
        <tbody>
          {players.filter(p => p.name.toLowerCase().includes(searchTerm.toLowerCase())).map((p, i) => (
            <tr key={p.name} onClick={() => !editingPlayer && onPlayerSelect(p.name)} className={editingPlayer === p.name ? '' : 'clickable-row'}>
              <td>{i + 1}</td>
              <td>
                {editingPlayer === p.name ? (
                  <div className="inline-form" onClick={e => e.stopPropagation()}>
                    <input
                      type="text"
                      value={editName}
                      onChange={e => setEditName(e.target.value)}
                      onKeyDown={e => {
                        if (e.key === 'Enter') handleRename(p.name);
                        if (e.key === 'Escape') cancelEditing();
                      }}
                      autoFocus
                      aria-label="Edit player name"
                    />
                    <button className="action-button" onClick={(e) => { e.stopPropagation(); handleRename(p.name); }}>Save</button>
                    <button className="action-button" onClick={(e) => { e.stopPropagation(); cancelEditing(); }}>Cancel</button>
                  </div>
                ) : (
                  p.name
                )}
              </td>
              <td>{Math.round(p.rating)}</td>
              {canEdit && (
                <td>
                  {editingPlayer !== p.name && (
                    <button
                      className="edit-button"
                      onClick={(e) => startEditing(p.name, e)}
                      title="Rename player"
                      aria-label={`Rename ${p.name}`}
                    >
                      ✏️
                    </button>
                  )}
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default PlayerList;
