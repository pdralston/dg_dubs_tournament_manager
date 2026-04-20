import React, { useState, useEffect } from 'react';
import { API_BASE_URL } from '../config/api';
import { User } from '../types';

interface ManagedUser {
  user_id: number;
  username: string;
  role: string;
  is_active: boolean;
  created_at: string | null;
}

interface AdminProps {
  currentUser: User;
  onUserUpdated: (user: User) => void;
}

const PAYOUT_DEFAULTS_KEY = 'dgdubs_payout_defaults';
const FACTORY_PAYOUT_DEFAULTS = { buy_in_per_player: 9, third_place: 20, second_place: 40 };

function loadPayoutDefaults() {
  try {
    const saved = localStorage.getItem(PAYOUT_DEFAULTS_KEY);
    return saved ? { ...FACTORY_PAYOUT_DEFAULTS, ...JSON.parse(saved) } : { ...FACTORY_PAYOUT_DEFAULTS };
  } catch { return { ...FACTORY_PAYOUT_DEFAULTS }; }
}

const Admin: React.FC<AdminProps> = ({ currentUser, onUserUpdated }) => {
  const [adminTab, setAdminTab] = useState<'users' | 'season'>('users');
  const isAdmin = currentUser.role === 'admin';

  // ── User Management state ────────────────────────
  const [users, setUsers] = useState<ManagedUser[]>([]);
  const [usersLoading, setUsersLoading] = useState(true);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newUsername, setNewUsername] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [newRole, setNewRole] = useState('director');
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editUsername, setEditUsername] = useState('');
  const [editPassword, setEditPassword] = useState('');
  const [editRole, setEditRole] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // ── Payout Settings state ────────────────────────
  const [payoutSettings, setPayoutSettings] = useState(() => loadPayoutDefaults());
  const isCustomPayout = JSON.stringify(loadPayoutDefaults()) !== JSON.stringify(FACTORY_PAYOUT_DEFAULTS);

  // ── Archive state ───────────────────────────────
  const [archiveStep, setArchiveStep] = useState<'idle' | 'warning' | 'form'>('idle');
  const [archiveSeasonName, setArchiveSeasonName] = useState('');
  const [archivePreview, setArchivePreview] = useState<any>(null);
  const [archiveLoading, setArchiveLoading] = useState(false);

  const fetchUsers = async () => {
    if (isAdmin) {
      try {
        const res = await fetch(`${API_BASE_URL}/api/auth/users`, { credentials: 'include' });
        if (res.ok) setUsers(await res.json());
      } catch {} finally { setUsersLoading(false); }
    } else {
      setUsers([{ user_id: currentUser.user_id, username: currentUser.username, role: currentUser.role, is_active: true, created_at: null }]);
      setUsersLoading(false);
    }
  };

  useEffect(() => { fetchUsers(); }, []);

  // ── User CRUD ────────────────────────────────────
  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(''); setSuccess('');
    if (newPassword.length < 8) { setError('Password must be at least 8 characters'); return; }
    try {
      const res = await fetch(`${API_BASE_URL}/api/auth/users`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
        body: JSON.stringify({ username: newUsername, password: newPassword, role: newRole })
      });
      if (res.ok) {
        setSuccess(`User "${newUsername}" created`);
        setNewUsername(''); setNewPassword(''); setNewRole('director'); setShowCreateForm(false);
        fetchUsers();
      } else { const d = await res.json(); setError(d.error || 'Failed to create user'); }
    } catch { setError('Network error'); }
  };

  const startEdit = (u: ManagedUser) => {
    setEditingId(u.user_id); setEditUsername(u.username); setEditPassword(''); setEditRole(u.role);
    setError(''); setSuccess('');
  };

  const handleSave = async () => {
    if (!editingId) return;
    setError(''); setSuccess('');
    const body: any = { username: editUsername };
    if (editPassword) body.password = editPassword;
    if (isAdmin) body.role = editRole;
    try {
      const res = await fetch(`${API_BASE_URL}/api/auth/users/${editingId}`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
        body: JSON.stringify(body)
      });
      if (res.ok) {
        const updated = await res.json();
        setSuccess('User updated'); setEditingId(null); fetchUsers();
        if (editingId === currentUser.user_id) {
          onUserUpdated({ ...currentUser, username: updated.username, role: updated.role });
        }
      } else { const d = await res.json(); setError(d.error || 'Failed to update'); }
    } catch { setError('Network error'); }
  };

  // ── Archive ───────────────────────────────────────
  const loadArchivePreview = async () => {
    setArchiveLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/archive/preview`, { credentials: 'include' });
      if (res.ok) setArchivePreview(await res.json());
    } catch {} finally { setArchiveLoading(false); }
    setArchiveStep('form');
  };

  const performArchive = async () => {
    if (!archiveSeasonName.trim()) return;
    setArchiveLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/archive`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, credentials: 'include',
        body: JSON.stringify({ season_name: archiveSeasonName.trim() })
      });
      if (res.ok) {
        setSuccess(`Season "${archiveSeasonName.trim()}" archived successfully.`);
        setArchiveStep('idle'); setArchiveSeasonName(''); setArchivePreview(null);
      } else {
        const d = await res.json();
        setError(d.error || 'Archive failed');
      }
    } catch { setError('Archive failed'); }
    finally { setArchiveLoading(false); }
  };

  // ── Payout Settings ──────────────────────────────
  const savePayoutDefaults = () => {
    localStorage.setItem(PAYOUT_DEFAULTS_KEY, JSON.stringify(payoutSettings));
    setSuccess('Payout settings saved as default.');
  };

  const resetPayoutDefaults = () => {
    localStorage.removeItem(PAYOUT_DEFAULTS_KEY);
    setPayoutSettings({ ...FACTORY_PAYOUT_DEFAULTS });
  };

  return (
    <div className="page-content">
      <h2>{isAdmin ? 'Admin' : 'Profile'}</h2>

      <div className="admin-tabs">
        <button className={adminTab === 'users' ? 'active' : ''} onClick={() => { setAdminTab('users'); setError(''); setSuccess(''); }}>
          User Management
        </button>
        <button className={adminTab === 'season' ? 'active' : ''} onClick={() => { setAdminTab('season'); setError(''); setSuccess(''); }}>
          Season Management
        </button>
      </div>

      {error && <div className="error-message" role="alert">{error}</div>}
      {success && <div className="success-message">{success}</div>}

      {/* ── User Management Tab ─────────────────────── */}
      {adminTab === 'users' && (
        <>
          {isAdmin && (
            <div className="page-header" style={{ marginTop: '15px' }}>
              <h3>Users</h3>
              <button className="action-button" onClick={() => { setShowCreateForm(!showCreateForm); setEditingId(null); }}>
                {showCreateForm ? 'Cancel' : '+ Add User'}
              </button>
            </div>
          )}

          {showCreateForm && isAdmin && (
            <form className="new-player-form" onSubmit={handleCreate}>
              <h3>Create User</h3>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: '15px', alignItems: 'end' }}>
                <div className="form-group">
                  <label htmlFor="new-user">Username:</label>
                  <input id="new-user" type="text" value={newUsername} onChange={e => setNewUsername(e.target.value)} required minLength={3} />
                </div>
                <div className="form-group">
                  <label htmlFor="new-pass">Password:</label>
                  <input id="new-pass" type="password" value={newPassword} onChange={e => setNewPassword(e.target.value)} required minLength={8} autoComplete="new-password" />
                </div>
                <div className="form-group">
                  <label htmlFor="new-role">Role:</label>
                  <select id="new-role" value={newRole} onChange={e => setNewRole(e.target.value)}>
                    <option value="director">Director</option>
                    <option value="admin">Admin</option>
                  </select>
                </div>
                <button type="submit" className="action-button">Create</button>
              </div>
            </form>
          )}

          {usersLoading ? <div className="loading">Loading...</div> : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Username</th>
                  <th>Role</th>
                  {isAdmin && <th>Status</th>}
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {users.map(u => (
                  <tr key={u.user_id}>
                    {editingId === u.user_id ? (
                      <>
                        <td><input type="text" className="score-input" style={{ width: '150px' }} value={editUsername} onChange={e => setEditUsername(e.target.value)} /></td>
                        <td>
                          {isAdmin ? (
                            <select value={editRole} onChange={e => setEditRole(e.target.value)} style={{ padding: '8px', background: '#0f0f1a', color: '#e0e0e0', border: '1px solid #333', borderRadius: '4px' }}>
                              <option value="director">Director</option>
                              <option value="admin">Admin</option>
                            </select>
                          ) : u.role}
                        </td>
                        {isAdmin && <td>{u.is_active ? 'Active' : 'Inactive'}</td>}
                        <td>
                          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                            <input type="password" className="score-input" style={{ width: '120px' }} placeholder="New password" value={editPassword} onChange={e => setEditPassword(e.target.value)} autoComplete="new-password" />
                            <button className="action-button" style={{ padding: '5px 12px', fontSize: '12px' }} onClick={handleSave}>Save</button>
                            <button className="action-button secondary" style={{ padding: '5px 12px', fontSize: '12px' }} onClick={() => setEditingId(null)}>Cancel</button>
                          </div>
                        </td>
                      </>
                    ) : (
                      <>
                        <td>{u.username}</td>
                        <td>{u.role}</td>
                        {isAdmin && <td>{u.is_active ? 'Active' : 'Inactive'}</td>}
                        <td>
                          {(isAdmin || u.user_id === currentUser.user_id) && (
                            <button className="action-button secondary" style={{ padding: '5px 12px', fontSize: '12px' }} onClick={() => startEdit(u)}>Edit</button>
                          )}
                        </td>
                      </>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </>
      )}

      {/* ── Season Management Tab ───────────────────── */}
      {adminTab === 'season' && (
        <>
          {/* Archive Section — admin only */}
          {isAdmin && (
            <div className="season-section">
              <h3>Archive Season</h3>
              <p className="hint">Archiving ends the current season, preserves historical data, and prepares the system for a new season. This action cannot be undone.</p>
              <button className="action-button" onClick={() => setArchiveStep('warning')}>Archive Season</button>

              {archiveStep === 'warning' && (
                <div className="login-overlay">
                  <div className="login-modal">
                    <h2>⚠️ Warning</h2>
                    <p>The Archive action is <strong>destructive and cannot be reversed</strong>. It will reset seasonal data, remove inactive players, normalize ratings, and collapse the ace pot history.</p>
                    <div className="modal-buttons">
                      <button onClick={() => setArchiveStep('idle')}>Cancel</button>
                      <button onClick={loadArchivePreview}>Continue</button>
                    </div>
                  </div>
                </div>
              )}

              {archiveStep === 'form' && (
                <div className="login-overlay">
                  <div className="login-modal">
                    <h2>Archive Season</h2>
                    {archivePreview && (
                      <table className="data-table" style={{ marginBottom: '15px' }}>
                        <tbody>
                          <tr><td>Season Span</td><td>{archivePreview.start_date} — {archivePreview.end_date}</td></tr>
                          <tr><td>Events</td><td>{archivePreview.event_count}</td></tr>
                          <tr><td>Unique Participants</td><td>{archivePreview.unique_participants}</td></tr>
                          <tr><td>Total Participants</td><td>{archivePreview.total_participants}</td></tr>
                        </tbody>
                      </table>
                    )}
                    <div className="form-group">
                      <label htmlFor="season-name">Season Name:</label>
                      <input id="season-name" type="text" placeholder="e.g. Spring 2026" value={archiveSeasonName} onChange={e => setArchiveSeasonName(e.target.value)} />
                    </div>
                    <div className="modal-buttons">
                      <button onClick={() => { setArchiveStep('idle'); setArchiveSeasonName(''); }}>Cancel</button>
                      <button onClick={performArchive} disabled={archiveLoading || !archiveSeasonName.trim()}>
                        {archiveLoading ? 'Archiving...' : 'Perform Archive'}
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Payout Settings — admin and director */}
          <div className="season-section">
            <h3>Payout Settings</h3>
            <p className="hint">These values are used as defaults when creating new tournaments. They can be overridden per-tournament.</p>

            <div className="payout-form">
              <div className="form-group">
                <label htmlFor="buy-in">Buy-in per Player ($):</label>
                <input id="buy-in" type="number" min="0" step="0.25"
                  value={payoutSettings.buy_in_per_player}
                  onChange={e => setPayoutSettings({ ...payoutSettings, buy_in_per_player: parseFloat(e.target.value) || 0 })} />
              </div>

              <div className="form-group">
                <label htmlFor="third-place">3rd Place Payout ($):</label>
                <input id="third-place" type="number" min="0" step="1"
                  value={payoutSettings.third_place}
                  onChange={e => setPayoutSettings({ ...payoutSettings, third_place: parseFloat(e.target.value) || 0 })} />
              </div>

              <div className="form-group">
                <label htmlFor="second-place">2nd Place Payout ($):</label>
                <input id="second-place" type="number" min="0" step="1"
                  value={payoutSettings.second_place}
                  onChange={e => setPayoutSettings({ ...payoutSettings, second_place: parseFloat(e.target.value) || 0 })} />
              </div>
            </div>

            <div className="payout-preview">
              <h4>Preview (sample: 8 teams, 16 players)</h4>
              {(() => {
                const pot = payoutSettings.buy_in_per_player * 16;
                const third = payoutSettings.third_place;
                const second = payoutSettings.second_place;
                const first = pot - second - third;
                return (
                  <table className="data-table" style={{ maxWidth: '300px' }}>
                    <tbody>
                      <tr><td>Total pot</td><td>${pot.toFixed(2)}</td></tr>
                      <tr><td>1st place</td><td>${first.toFixed(2)}</td></tr>
                      <tr><td>2nd place</td><td>${second.toFixed(2)}</td></tr>
                      <tr><td>3rd place</td><td>${third.toFixed(2)}</td></tr>
                    </tbody>
                  </table>
                );
              })()}
            </div>

            <div style={{ display: 'flex', gap: '10px', marginTop: '15px' }}>
              <button className="action-button" onClick={savePayoutDefaults}>Save as Default</button>
              {isCustomPayout && (
                <button className="action-button secondary" onClick={resetPayoutDefaults}>Reset to Original Default</button>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default Admin;
