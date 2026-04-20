import React, { useState, useEffect } from 'react';
import { API_BASE_URL } from '../config/api';

interface PlayerDetailData {
  name: string;
  rating: number;
  tournaments_played: number;
  seasonal_cash: number;
  lifetime_cash: number;
  seasons: { id: number | null; name: string }[];
  history: {
    date: string; position: number; expected_position: number;
    old_rating: number; new_rating: number; change: number;
    with_ghost: boolean; tournament_id?: number;
  }[];
}

interface TournamentDetailData {
  tournament_id: number;
  date: string;
  course: string;
  status: string;
  ace_pot_recipient?: string | null;
  results: { team: string[]; position: number; score: number; team_rating: number; payout?: number }[];
}

interface PlayerDetailsProps {
  playerName: string;
  onBack: () => void;
}

const PlayerDetails: React.FC<PlayerDetailsProps> = ({ playerName, onBack }) => {
  const [player, setPlayer] = useState<PlayerDetailData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedSeason, setSelectedSeason] = useState<string>('null');
  const [tournamentModal, setTournamentModal] = useState<TournamentDetailData | null>(null);
  const [historyLoading, setHistoryLoading] = useState(false);

  const fetchPlayer = async (seasonId?: string) => {
    try {
      const sid = seasonId ?? selectedSeason;
      const url = sid && sid !== 'null'
        ? `${API_BASE_URL}/api/players/${encodeURIComponent(playerName)}?season_id=${sid}`
        : `${API_BASE_URL}/api/players/${encodeURIComponent(playerName)}`;
      const res = await fetch(url, { credentials: 'include' });
      if (res.ok) setPlayer(await res.json());
      else setError('Player not found');
    } catch { setError('Failed to load player details'); }
    finally { setLoading(false); setHistoryLoading(false); }
  };

  useEffect(() => { fetchPlayer(); }, [playerName]);

  const handleSeasonChange = (seasonId: string) => {
    setSelectedSeason(seasonId);
    setHistoryLoading(true);
    fetchPlayer(seasonId);
  };

  const openTournament = async (tournamentId?: number, date?: string) => {
    if (!tournamentId && !date) return;
    try {
      let url: string;
      if (tournamentId) {
        url = `${API_BASE_URL}/api/tournaments/${tournamentId}`;
      } else {
        // For current season entries without tournament_id, find by date
        const listRes = await fetch(`${API_BASE_URL}/api/tournaments`, { credentials: 'include' });
        if (!listRes.ok) return;
        const tournaments = await listRes.json();
        const match = tournaments.find((t: any) => t.date === date);
        if (!match) return;
        url = `${API_BASE_URL}/api/tournaments/${match.tournament_id}`;
      }
      const res = await fetch(url, { credentials: 'include' });
      if (res.ok) setTournamentModal(await res.json());
    } catch {}
  };

  if (loading) return <div className="loading">Loading...</div>;
  if (error || !player) return <div className="error-message">{error}</div>;

  const currentHistory = player.history;
  const avgPlace = currentHistory.length > 0
    ? (currentHistory.reduce((sum, h) => sum + h.position, 0) / currentHistory.length).toFixed(1)
    : null;

  return (
    <div className="page-content">
      <button className="back-button" onClick={onBack}>← Back to Players</button>
      <div className="player-header">
        <h2>{player.name}</h2>
        <div className="player-stats">
          <span className="stat">Rating: <strong>{Math.round(player.rating)}</strong></span>
          <span className="stat">Tournaments: <strong>{player.tournaments_played}</strong></span>
          {avgPlace && <span className="stat">Avg Place: <strong>{avgPlace}</strong></span>}
          <span className="stat">Season $: <strong>${player.seasonal_cash.toFixed(2)}</strong></span>
          <span className="stat">Lifetime $: <strong>${player.lifetime_cash.toFixed(2)}</strong></span>
        </div>
      </div>

      {player.seasons && player.seasons.length > 1 && (
        <div className="season-selector">
          <label htmlFor="season-select">Season: </label>
          <select id="season-select" value={selectedSeason} onChange={e => handleSeasonChange(e.target.value)}>
            {player.seasons.map(s => (
              <option key={s.id ?? 'current'} value={s.id === null ? 'null' : s.id}>{s.name}</option>
            ))}
          </select>
        </div>
      )}

      {historyLoading ? (
        <div className="loading">Loading history...</div>
      ) : currentHistory.length > 0 ? (
        <table className="data-table">
          <thead>
            <tr>
              <th>Date</th>
              <th>Position</th>
              <th>Expected</th>
              <th>Rating Change</th>
              <th>New Rating</th>
            </tr>
          </thead>
          <tbody>
            {currentHistory.slice().reverse().map((h, i) => (
              <tr key={i} className="clickable-row" onClick={() => openTournament(h.tournament_id, h.date)}>
                <td>{h.date}</td>
                <td>{h.position}</td>
                <td>{h.expected_position.toFixed(1)}</td>
                <td className={h.change >= 0 ? 'positive' : 'negative'}>
                  {h.change >= 0 ? '+' : ''}{h.change.toFixed(1)}
                </td>
                <td>{Math.round(h.new_rating)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p>No tournament history for this season.</p>
      )}

      {/* Tournament Detail Modal */}
      {tournamentModal && (
        <div className="login-overlay" onClick={() => setTournamentModal(null)}>
          <div className="tournament-modal" onClick={e => e.stopPropagation()}>
            <div className="tournament-detail-header">
              <h2>{tournamentModal.course}</h2>
              <span className="tournament-date">{tournamentModal.date}</span>
            </div>
            {tournamentModal.results && tournamentModal.results.length > 0 ? (
              <table className="data-table">
                <thead>
                  <tr><th>Pos</th><th>Team</th><th>Score</th><th>Team Rating</th><th>Payout</th></tr>
                </thead>
                <tbody>
                  {tournamentModal.results.map((r, i) => (
                    <tr key={i} className={r.team.includes(player.name) ? 'highlight-row' : ''}>
                      <td>{r.position}</td>
                      <td>{r.team.join(' & ')}</td>
                      <td>{r.score}</td>
                      <td>{Math.round(r.team_rating)}</td>
                      <td>{r.payout && r.payout > 0 ? `$${r.payout.toFixed(2)}` : ''}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p>No results available.</p>
            )}
            {tournamentModal.ace_pot_recipient && (
              <div className="ace-pot-callout">
                🎯 Ace Pot awarded to <strong>{tournamentModal.ace_pot_recipient}</strong>
              </div>
            )}
            <button className="action-button" style={{ marginTop: '15px' }} onClick={() => setTournamentModal(null)}>Close</button>
          </div>
        </div>
      )}
    </div>
  );
};

export default PlayerDetails;
