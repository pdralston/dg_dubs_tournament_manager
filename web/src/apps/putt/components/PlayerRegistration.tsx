import React, { useState } from 'react';
import { Player } from '../types/player';
import { API_BASE_URL } from '../config/api';

interface PlayerRegistrationProps {
  onPlayerAdded: (player: Player) => void;
}

const PlayerRegistration: React.FC<PlayerRegistrationProps> = ({ onPlayerAdded }) => {
  const [name, setName] = useState('');
  const [nickname, setNickname] = useState('');
  const [division, setDivision] = useState<'Pro' | 'Am' | 'Junior'>('Am');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/putt/players`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          player_name: name.trim(),
          nickname: nickname.trim() || null,
          division
        })
      });

      if (response.ok) {
        const result = await response.json();
        if (result.created && result.created.length > 0) {
          onPlayerAdded(result.created[0]);
          setName('');
          setNickname('');
          setDivision('Am');
        }
      } else {
        const error = await response.json();
        const errorMessage = error.errors ? error.errors.join('\n') : (error.error || 'Unknown error');
        alert(`Error registering player: ${errorMessage}`);
      }
    } catch (error) {
      console.error('Failed to register player:', error);
      alert('Network error: Failed to register player. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="player-registration">
      <h3>Register Player</h3>
      <input
        type="text"
        placeholder="Player Name"
        value={name}
        onChange={(e) => setName(e.target.value)}
        required
      />
      <input
        type="text"
        placeholder="Nickname (optional)"
        value={nickname}
        onChange={(e) => setNickname(e.target.value)}
      />
      <select value={division} onChange={(e) => setDivision(e.target.value as 'Pro' | 'Am' | 'Junior')}>
        <option value="Am">Amateur</option>
        <option value="Pro">Professional</option>
        <option value="Junior">Junior</option>
      </select>
      <button type="submit" disabled={loading || !name.trim()}>
        {loading ? 'Adding...' : 'Add Player'}
      </button>
    </form>
  );
};

export default PlayerRegistration;
