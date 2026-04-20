import React, { useState, useEffect } from 'react';
import { API_BASE_URL } from '../config/api';
import { Player } from '../types';

interface TournamentSummary {
  tournament_id: number;
  date: string;
  course: string;
  teams: number;
  status: string;
}

interface TournamentDetail extends TournamentSummary {
  participants: { name: string; rating: number; ace_pot_buy_in: boolean }[];
  results: { team: string[]; position: number; expected_position: number; score: number; team_rating: number; payout: number }[];
  ace_pot_paid?: boolean;
  ace_pot_recipient?: string | null;
}

interface GeneratedTeam {
  player1: string;
  player2: string;
  team_rating: number;
  expected_position: number;
}

interface TournamentsProps {
  userRole: string;
}

type View = 'list' | 'create' | 'detail';

const Tournaments: React.FC<TournamentsProps> = ({ userRole }) => {
  const [view, setView] = useState<View>('list');
  const [tournaments, setTournaments] = useState<TournamentSummary[]>([]);
  const [loading, setLoading] = useState(true);

  // Create state
  const [pendingId, setPendingId] = useState<number | null>(null);
  const [course, setCourse] = useState('');
  const [date, setDate] = useState(() => {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  });
  const [availablePlayers, setAvailablePlayers] = useState<Player[]>([]);
  const [selectedPlayers, setSelectedPlayers] = useState<{ name: string; rating: number; ace_pot: boolean }[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [showNewPlayer, setShowNewPlayer] = useState(false);
  const [newPlayer, setNewPlayer] = useState({ name: '', rating: '1000' });

  // Detail state
  const [detail, setDetail] = useState<TournamentDetail | null>(null);
  const [generatedTeams, setGeneratedTeams] = useState<GeneratedTeam[] | null>(null);
  const [teamScores, setTeamScores] = useState<{ player1: string; player2: string; score: string }[]>([]);
  const [acePotPaid, setAcePotPaid] = useState(false);
  const [acePotRecipients, setAcePotRecipients] = useState<Set<string>>(new Set());

  // Tie resolution
  const [tieModal, setTieModal] = useState<{
    tournament_id: number; pot: number; first_payout: number; second_payout: number; third_payout: number;
    tied_teams: { player1: string; player2: string; position: number; score: number }[];
    manual_payouts: { player1: string; player2: string; payout: string }[];
  } | null>(null);

  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const canEdit = userRole === 'admin' || userRole === 'director';

  const fetchTournaments = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/tournaments`, { credentials: 'include' });
      if (res.ok) setTournaments(await res.json());
    } catch {} finally { setLoading(false); }
  };

  useEffect(() => { fetchTournaments(); }, []);

  const visibleTournaments = canEdit
    ? tournaments
    : tournaments.filter(t => t.status !== 'Pending');

  // ── Create flow ──────────────────────────────────

  const startCreate = async () => {
    setError('');
    setCourse('');
    setSelectedPlayers([]);
    setSearchTerm('');
    setGeneratedTeams(null);

    try {
      const [playersRes, pendingRes] = await Promise.all([
        fetch(`${API_BASE_URL}/api/players`, { credentials: 'include' }),
        fetch(`${API_BASE_URL}/api/tournaments/pending`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({ course: '', date })
        })
      ]);
      if (playersRes.ok) setAvailablePlayers(await playersRes.json());
      if (pendingRes.ok) {
        const data = await pendingRes.json();
        setPendingId(data.tournament_id);
        pendingIdRef.current = data.tournament_id;
      }
    } catch {}

    setView('create');
  };

  const pendingIdRef = React.useRef<number | null>(null);

  const updatePendingField = (field: string, value: string) => {
    const tid = pendingIdRef.current || pendingId;
    if (tid) {
      fetch(`${API_BASE_URL}/api/tournaments/${tid}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ [field]: value })
      }).catch(() => {});
    }
  };

  const addPlayer = async (player: Player) => {
    if (selectedPlayers.find(s => s.name === player.name)) return;
    const tid = pendingIdRef.current;
    if (!tid) { setError('Tournament not initialized'); return; }

    try {
      await fetch(`${API_BASE_URL}/api/tournaments/${tid}/players`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ name: player.name, ace_pot_buy_in: false })
      });
      setSelectedPlayers(prev => [...prev, { name: player.name, rating: player.rating, ace_pot: false }]);
    } catch { setError('Failed to add player'); }
  };

  const removePlayer = async (name: string) => {
    if (pendingId) {
      await fetch(`${API_BASE_URL}/api/tournaments/${pendingId}/players/${encodeURIComponent(name)}`, {
        method: 'DELETE', credentials: 'include'
      }).catch(() => {});
    }
    setSelectedPlayers(prev => prev.filter(p => p.name !== name));
  };

  const toggleAcePot = async (name: string) => {
    const player = selectedPlayers.find(p => p.name === name);
    if (!player || !pendingId) return;
    const newVal = !player.ace_pot;
    await fetch(`${API_BASE_URL}/api/tournaments/${pendingId}/players`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ name, ace_pot_buy_in: newVal })
    }).catch(() => {});
    setSelectedPlayers(prev => prev.map(p => p.name === name ? { ...p, ace_pot: newVal } : p));
  };

  const handleNewPlayer = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    try {
      const res = await fetch(`${API_BASE_URL}/api/players`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ name: newPlayer.name, rating: parseFloat(newPlayer.rating) })
      });
      if (res.ok) {
        const created = await res.json();
        setAvailablePlayers(prev => [...prev, created]);
        await addPlayer(created);
        setNewPlayer({ name: '', rating: '1000' });
        setShowNewPlayer(false);
      } else {
        const data = await res.json();
        setError(data.error || 'Failed to add player');
      }
    } catch { setError('Network error'); }
  };

  const handleGenerate = async () => {
    if (!course.trim()) { setError('Course name is required'); return; }
    const tid = pendingIdRef.current;
    if (!tid) { setError('Tournament not initialized'); return; }

    setError('');
    setSubmitting(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/tournaments/${tid}/generate`, {
        method: 'POST', credentials: 'include'
      });
      if (res.ok) {
        const data = await res.json();
        setGeneratedTeams(data.teams);
        setTeamScores(data.teams.map((t: GeneratedTeam) => ({ player1: t.player1, player2: t.player2, score: '' })));
        // Reload tournament detail
        openDetail(tid);
      } else {
        const data = await res.json();
        setError(data.error || 'Failed to generate teams');
      }
    } catch { setError('Network error'); }
    finally { setSubmitting(false); }
  };

  // ── Detail / Record flow ─────────────────────────

  const openDetail = async (tid: number) => {
    setError('');
    try {
      const res = await fetch(`${API_BASE_URL}/api/tournaments/${tid}`, { credentials: 'include' });
      if (res.ok) {
        const data: TournamentDetail = await res.json();
        setDetail(data);
        if (data.status === 'In Progress' && !generatedTeams) {
          // Re-generate team display from participants
          const pRes = await fetch(`${API_BASE_URL}/api/teams`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ players: data.participants.map(p => p.name) })
          });
          if (pRes.ok) {
            const teams: GeneratedTeam[] = await pRes.json();
            setGeneratedTeams(teams);
            setTeamScores(teams.map(t => ({ player1: t.player1, player2: t.player2, score: '' })));
          }
        }
        setAcePotPaid(false);
        setAcePotRecipients(new Set());
        setView('detail');
      }
    } catch { setError('Failed to load tournament'); }
  };

  const editPending = async (tid: number) => {
    setError('');
    try {
      const res = await fetch(`${API_BASE_URL}/api/tournaments/${tid}`, { credentials: 'include' });
      if (res.ok) {
        const data: TournamentDetail = await res.json();
        setPendingId(tid);
        pendingIdRef.current = tid;
        setCourse(data.course);
        setDate(data.date);
        setSelectedPlayers(data.participants.map(p => ({ name: p.name, rating: p.rating, ace_pot: p.ace_pot_buy_in })));
        // Fetch all players
        const pRes = await fetch(`${API_BASE_URL}/api/players`, { credentials: 'include' });
        if (pRes.ok) setAvailablePlayers(await pRes.json());
        setGeneratedTeams(null);
        setView('create');
      }
    } catch { setError('Failed to load tournament'); }
  };

  const handleRecord = async (manualPayouts?: { player1: string; player2: string; payout: number }[]) => {
    const tid = tieModal ? tieModal.tournament_id : detail?.tournament_id;
    if (!tid && !detail) return;
    setError('');

    // If coming from tie modal, submit manual payouts to existing tournament
    if (manualPayouts && tieModal) {
      setSubmitting(true);
      try {
        const res = await fetch(`${API_BASE_URL}/api/tournaments/${tieModal.tournament_id}/record`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({
            team_results: teamScores.sort((a, b) => parseInt(a.score) - parseInt(b.score)).map(t => ({ player1: t.player1, player2: t.player2, score: parseInt(t.score) })),
            payout_config: loadPayoutConfig(),
            manual_payouts: manualPayouts.map(mp => ({ ...mp, payout: mp.payout }))
          })
        });
        // This path won't work since tournament is already recorded.
        // We need a separate endpoint. Let me use a different approach.
      } catch {} finally { setSubmitting(false); }
      return;
    }

    if (!detail) return;
    const incomplete = teamScores.filter(t => !t.score);
    if (incomplete.length > 0) { setError('All teams must have a score'); return; }

    const sorted = [...teamScores].sort((a, b) => parseInt(a.score) - parseInt(b.score));
    setSubmitting(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/tournaments/${detail.tournament_id}/record`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          team_results: sorted.map(t => ({ player1: t.player1, player2: t.player2, score: parseInt(t.score) })),
          payout_config: loadPayoutConfig(),
        })
      });

      if (!res.ok) {
        const data = await res.json();
        setError(data.error || 'Failed to record');
        return;
      }

      const result = await res.json();

      // Handle tie — show modal for manual payout entry
      if (result.needs_manual_payout) {
        setTieModal({
          tournament_id: result.tournament_id,
          pot: result.pot,
          first_payout: result.first_payout,
          second_payout: result.second_payout,
          third_payout: result.third_payout,
          tied_teams: result.tied_teams,
          manual_payouts: result.tied_teams.map((t: any) => ({ player1: t.player1, player2: t.player2, payout: '' })),
        });
        setSubmitting(false);
        return;
      }

      await processAcePot(result.tournament_id);
      finishRecord(result.tournament_id);
    } catch { setError('Network error'); }
    finally { setSubmitting(false); }
  };

  const loadPayoutConfig = () => {
    try {
      const saved = localStorage.getItem('dgdubs_payout_defaults');
      return saved ? JSON.parse(saved) : { buy_in_per_player: 9, third_place: 20, second_place: 40 };
    } catch { return { buy_in_per_player: 9, third_place: 20, second_place: 40 }; }
  };

  const submitManualPayouts = async () => {
    if (!tieModal) return;
    setSubmitting(true);
    setError('');
    try {
      const res = await fetch(`${API_BASE_URL}/api/tournaments/${tieModal.tournament_id}/payouts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          payouts: tieModal.manual_payouts.map(mp => ({
            player1: mp.player1, player2: mp.player2, payout: parseFloat(mp.payout) || 0
          }))
        })
      });
      if (!res.ok) {
        const data = await res.json();
        setError(data.error || 'Failed to apply payouts');
        return;
      }
      await processAcePot(tieModal.tournament_id);
      const tid = tieModal.tournament_id;
      setTieModal(null);
      finishRecord(tid);
    } catch { setError('Network error'); }
    finally { setSubmitting(false); }
  };

  const processAcePot = async (tournamentId: number) => {
    if (!detail) return;
    const buyIns = detail.participants.filter(p => p.ace_pot_buy_in).map(p => p.name);
    if (buyIns.length > 0 || (acePotPaid && acePotRecipients.size > 0)) {
      await fetch(`${API_BASE_URL}/api/ace-pot/tournament`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          tournament_id: tournamentId,
          buy_in_players: buyIns,
          payout_recipients: acePotPaid ? Array.from(acePotRecipients) : []
        })
      }).catch(() => {});
    }
  };

  const finishRecord = (newTid?: number) => {
    const tid = newTid || detail?.tournament_id;
    setGeneratedTeams(null);
    setPendingId(null);
    pendingIdRef.current = null;
    if (tid) {
      openDetail(tid);
    } else {
      setView('list');
      fetchTournaments();
    }
  };

  const handleDelete = async (tid: number) => {
    if (!window.confirm('Delete this tournament?')) return;
    await fetch(`${API_BASE_URL}/api/tournaments/${tid}`, { method: 'DELETE', credentials: 'include' }).catch(() => {});
    fetchTournaments();
  };

  const backToList = () => {
    setView('list');
    setDetail(null);
    setGeneratedTeams(null);
    fetchTournaments();
  };

  const filteredPlayers = availablePlayers
    .filter(p => !selectedPlayers.find(s => s.name === p.name) && p.name.toLowerCase().includes(searchTerm.toLowerCase()))
    .sort((a, b) => a.name.localeCompare(b.name));

  const acePotCount = selectedPlayers.filter(p => p.ace_pot).length;

  // ── List view ────────────────────────────────────

  if (view === 'list') {
    if (loading) return <div className="loading">Loading tournaments...</div>;
    return (
      <div className="page-content tournament-directory">
        <div className="page-header">
          <h2>Tournaments</h2>
          {canEdit && (
            <button className="create-tournament-button" onClick={startCreate}>Create Tournament</button>
          )}
        </div>
        <table className="data-table">
          <thead>
            <tr>
              <th>Date</th>
              <th>Course</th>
              <th>Status</th>
              <th>Teams</th>
              {userRole === 'admin' && <th></th>}
            </tr>
          </thead>
          <tbody>
            {visibleTournaments.map(t => (
              <tr
                key={t.tournament_id}
                className="clickable-row"
                onClick={() => {
                  if (t.status === 'Pending' && canEdit) editPending(t.tournament_id);
                  else openDetail(t.tournament_id);
                }}
              >
                <td>{t.date}</td>
                <td>{t.course}</td>
                <td><span className={`status-badge status-${t.status.toLowerCase().replace(' ', '-')}`}>{t.status}</span></td>
                <td>{t.teams}</td>
                {userRole === 'admin' && (
                  <td>
                    {t.status === 'Pending' && (
                      <button className="delete-button" onClick={(e) => { e.stopPropagation(); handleDelete(t.tournament_id); }}>Delete</button>
                    )}
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
        {visibleTournaments.length === 0 && <p className="empty-state">The season hasn't started yet, but when it does check back here to see all of the completed tournaments!</p>}
      </div>
    );
  }

  // ── Create view ──────────────────────────────────

  if (view === 'create') {
    return (
      <div className="tournament-creation">
        <button className="back-button" onClick={backToList}>← Back to Tournaments</button>
        <div className="page-header"><h2>Create Tournament</h2></div>
        {error && <div className="error-message" role="alert">{error}</div>}

        <div className="creation-form">
          <div className="form-section parent">
            <div>
              <label htmlFor="tc-course">Course:</label>
              <input id="tc-course" type="text" value={course} onChange={e => { setCourse(e.target.value); updatePendingField('course', e.target.value); }} required />
            </div>
            <div>
              <label htmlFor="tc-date">Tournament Date:</label>
              <input id="tc-date" type="date" value={date} onChange={e => { setDate(e.target.value); updatePendingField('date', e.target.value); }} />
            </div>
          </div>

          <div className="players-section">
            <div className="available-players">
              <h3>Available Players</h3>
              <input type="text" placeholder="Search players..." value={searchTerm} onChange={e => setSearchTerm(e.target.value)} className="search-input" aria-label="Search players" />
              <div className="player-list">
                {filteredPlayers.map(p => (
                  <div key={p.name} className="player-item">
                    <span>{p.name} ({Math.round(p.rating)})</span>
                    <button onClick={() => addPlayer(p)}>Add</button>
                  </div>
                ))}
              </div>
              <button className="new-player-button" onClick={() => setShowNewPlayer(true)}>Register New Player</button>
            </div>

            <div className="selected-players">
              <h3>Tournament Players ({selectedPlayers.length})</h3>
              <div className="ace-pot-summary">Ace Pot Buy-ins: {acePotCount} (${acePotCount}.00)</div>
              <div className="player-list">
                {selectedPlayers.map(p => (
                  <div key={p.name} className="player-item selected">
                    <span>{p.name} ({Math.round(p.rating)})</span>
                    <div className="player-controls">
                      <label className="ace-pot-checkbox">
                        <input type="checkbox" checked={p.ace_pot} onChange={() => toggleAcePot(p.name)} />
                        Ace Pot
                      </label>
                      <button onClick={() => removePlayer(p.name)}>Remove</button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {showNewPlayer && (
            <div className="new-player-form">
              <h3>Register New Player</h3>
              <form onSubmit={handleNewPlayer}>
                <input type="text" placeholder="Player Name" value={newPlayer.name} onChange={e => setNewPlayer({ ...newPlayer, name: e.target.value })} required />
                <select value={newPlayer.rating} onChange={e => setNewPlayer({ ...newPlayer, rating: e.target.value })}>
                  <option value="1300">A Player (1300)</option>
                  <option value="1000">B Player (1000)</option>
                </select>
                <div className="form-buttons">
                  <button type="submit">Add Player</button>
                  <button type="button" onClick={() => setShowNewPlayer(false)}>Cancel</button>
                </div>
              </form>
            </div>
          )}

          <div className="create-section">
            <button className="create-tournament-button" onClick={handleGenerate} disabled={submitting || selectedPlayers.length < 2 || !course.trim()}>
              {submitting ? 'Generating...' : 'Generate Teams'}
            </button>
          </div>
        </div>
      </div>
    );
  }

  // ── Detail view ──────────────────────────────────

  if (view === 'detail' && detail) {
    const allPlayers = generatedTeams
      ? generatedTeams.flatMap(t => [t.player1, t.player2]).filter(p => p !== 'Ghost Player')
      : detail.results.flatMap(r => r.team).filter(p => p !== 'Ghost Player');

    const toggleRecipient = (name: string) => {
      setAcePotRecipients(prev => { const n = new Set(prev); if (n.has(name)) n.delete(name); else n.add(name); return n; });
    };

    return (
      <div className="page-content">
        <button className="back-button" onClick={backToList}>← Back to Tournaments</button>
        <div className="tournament-detail-header">
          <h2>{detail.course}</h2>
          <span className="tournament-date">{detail.date}</span>
          <span className={`status-badge status-${detail.status.toLowerCase().replace(' ', '-')}`}>{detail.status}</span>
        </div>
        {error && <div className="error-message" role="alert">{error}</div>}

        {/* In Progress: show generated teams with score entry for admins */}
        {detail.status === 'In Progress' && generatedTeams && (
          <>
            <h3>Teams</h3>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Exp. Pos</th>
                  <th>Player 1</th>
                  <th>Player 2</th>
                  <th>Team Rating</th>
                  {canEdit && <th>Score</th>}
                </tr>
              </thead>
              <tbody>
                {generatedTeams.map((t, i) => (
                  <tr key={i}>
                    <td>{t.expected_position.toFixed(1)}</td>
                    <td>{t.player1}</td>
                    <td>{t.player2}</td>
                    <td>{Math.round(t.team_rating)}</td>
                    {canEdit && (
                      <td>
                        <input type="number" className="score-input" value={teamScores[i]?.score || ''}
                          onChange={e => setTeamScores(prev => prev.map((s, j) => j === i ? { ...s, score: e.target.value } : s))}
                          placeholder="Score" aria-label={`Score for ${t.player1} & ${t.player2}`} />
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>

            {canEdit && (
              <>
                <div className="ace-pot-section">
                  <h3>Ace Pot</h3>
                  <label className="checkbox-label ace-paid-toggle">
                    <input type="checkbox" checked={acePotPaid} onChange={e => setAcePotPaid(e.target.checked)} />
                    Ace pot was hit this tournament
                  </label>
                  {acePotPaid && (
                    <div className="ace-subsection">
                      <h4>Payout Recipients</h4>
                      <div className="player-checkboxes">
                        {allPlayers.map(p => (
                          <label key={p} className="checkbox-label">
                            <input type="checkbox" checked={acePotRecipients.has(p)} onChange={() => toggleRecipient(p)} />
                            {p}
                          </label>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
                <button className="action-button record-button" onClick={() => handleRecord()} disabled={submitting}>
                  {submitting ? 'Recording...' : 'Record Results'}
                </button>

                {/* Tie Resolution Modal */}
                {tieModal && (
                  <div className="login-overlay">
                    <div className="tournament-modal">
                      <h2>Tie Detected — Manual Payout</h2>
                      <p>Total pot: <strong>${tieModal.pot.toFixed(2)}</strong> | 1st: <strong>${tieModal.first_payout.toFixed(2)}</strong> | 2nd: <strong>${tieModal.second_payout.toFixed(2)}</strong> | 3rd: <strong>${tieModal.third_payout.toFixed(2)}</strong></p>
                      <p className="hint">Enter the payout amount for each tied team. Teams not receiving a payout should be $0.</p>
                      <table className="data-table">
                        <thead>
                          <tr><th>Team</th><th>Position</th><th>Score</th><th>Payout ($)</th></tr>
                        </thead>
                        <tbody>
                          {tieModal.manual_payouts.map((mp, i) => (
                            <tr key={i}>
                              <td>{mp.player1} & {mp.player2}</td>
                              <td>{tieModal.tied_teams[i].position}</td>
                              <td>{tieModal.tied_teams[i].score}</td>
                              <td>
                                <input type="number" className="score-input" step="0.01" min="0"
                                  value={mp.payout}
                                  onChange={e => setTieModal(prev => {
                                    if (!prev) return prev;
                                    const updated = [...prev.manual_payouts];
                                    updated[i] = { ...updated[i], payout: e.target.value };
                                    return { ...prev, manual_payouts: updated };
                                  })}
                                  aria-label={`Payout for ${mp.player1} & ${mp.player2}`}
                                />
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                      <div className="modal-buttons" style={{ marginTop: '15px' }}>
                        <button onClick={() => { const tid = tieModal.tournament_id; setTieModal(null); finishRecord(tid); }}>Skip Payouts</button>
                        <button onClick={submitManualPayouts} disabled={submitting}>
                          {submitting ? 'Applying...' : 'Apply Payouts'}
                        </button>
                      </div>
                    </div>
                  </div>
                )}
              </>
            )}
          </>
        )}

        {/* Completed: show results */}
        {detail.status === 'Completed' && detail.results.length > 0 && (
          <>
            <h3>Results</h3>
            <table className="data-table">
              <thead>
                <tr><th>Pos</th><th>Team</th><th>Score</th><th>Team Rating</th><th>Payout</th></tr>
              </thead>
              <tbody>
                {detail.results.map((r, i) => (
                  <tr key={i}>
                    <td>{r.position}</td>
                    <td>{r.team.join(' & ')}</td>
                    <td>{r.score}</td>
                    <td>{Math.round(r.team_rating)}</td>
                    <td>{r.payout > 0 ? `$${r.payout.toFixed(2)}` : ''}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {detail.ace_pot_recipient && (
              <div className="ace-pot-callout">
                🎯 Ace Pot awarded to <strong>{detail.ace_pot_recipient}</strong>
              </div>
            )}
          </>
        )}
      </div>
    );
  }

  return null;
};

export default Tournaments;
