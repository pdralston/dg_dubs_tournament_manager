// ⚠️ KNOWN GAP (2026-11-07) — user-management here is BROKEN against the
// consolidated DG-Rater backend, pending the §13 governance migration.
// This component still assumes DG-Putt's old single-axis auth:
//   • it calls POST /api/auth/reset-data, which does NOT exist on the shared
//     auth_api.py (deliberately not ported — unsafe on a multi-tenant backend);
//   • it uses `user_id` and Admin/Director role enums, but the shared `users`
//     model keys on `id` and authz is org_roles + org_memberships.
// The fix is to rebuild this tab on the governance model (per-app role chips,
// org-user provisioning via the future /api/org/* endpoints), NOT a patch.
// See docs/DG-Rater-2.0-Org-Governance-Design.md §13.8. The rest of the DG-Putt
// SPA (players, tournaments, brackets, scoring, ace-pot, archive, login/logout)
// works against the consolidated backend.
import React, { useState, useEffect } from 'react';
import { API_BASE_URL } from '../config/api';
import AdminAudit from './AdminAudit';
import TournamentEdit from './TournamentEdit';
import './Admin.css';

interface User {
  user_id: number;
  username: string;
  role: string;
  created_at: string;
}

interface Tournament {
  tournament_id: number;
  tournament_date: string;
  status: string;
  total_teams: number;
}

interface AdminProps {
  currentUser: { user_id: number; username: string; role: string };
}

const PAYOUT_DEFAULTS_KEY = 'dgputt_payout_defaults';
const FACTORY_PAYOUT_DEFAULTS = { mode: 'fixed' as 'fixed' | 'percentage', second_place_value: 20, buy_in_per_player: 5 };

export function loadPayoutDefaults() {
  try {
    const saved = localStorage.getItem(PAYOUT_DEFAULTS_KEY);
    return saved ? { ...FACTORY_PAYOUT_DEFAULTS, ...JSON.parse(saved) } : { ...FACTORY_PAYOUT_DEFAULTS };
  } catch {
    return { ...FACTORY_PAYOUT_DEFAULTS };
  }
}

const Admin: React.FC<AdminProps> = ({ currentUser }) => {
  const [activeAdminTab, setActiveAdminTab] = useState<'users' | 'audit' | 'tournaments' | 'payout'>('users');
  const [users, setUsers] = useState<User[]>([]);
  const [tournaments, setTournaments] = useState<Tournament[]>([]);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [formData, setFormData] = useState({ username: '', password: '', role: 'Director' });
  const [selectedTournamentId, setSelectedTournamentId] = useState<number | null>(null);

  // Payout settings state
  const [payoutSettings, setPayoutSettings] = useState(() => loadPayoutDefaults());
  const isCustomPayout = JSON.stringify(loadPayoutDefaults()) !== JSON.stringify(FACTORY_PAYOUT_DEFAULTS);

  // Archive state
  type AmLeader = { player_id: number; player_name: string; seasonal_points: number };
  type IncompleteTournament = { tournament_id: number; tournament_date: string; status: string };
  type ArchivePreview = {
    start_date: string | null;
    end_date: string | null;
    event_count: number;
    unique_participants: number;
    total_participants: number;
    incomplete_to_delete: IncompleteTournament[];
    am_leaders: AmLeader[];
    am_promotion_tie: boolean;
    can_archive: boolean;
  };
  type ArchiveStep = 'idle' | 'warning' | 'form' | 'tie';
  const [archiveStep, setArchiveStep] = useState<ArchiveStep>('idle');
  const [archiveSeasonName, setArchiveSeasonName] = useState('');
  const [archivePreview, setArchivePreview] = useState<ArchivePreview | null>(null);
  const [archiveLoading, setArchiveLoading] = useState(false);
  // Am-promotion tie resolution
  const [tiedLeaders, setTiedLeaders] = useState<AmLeader[]>([]);
  const [selectedPromotions, setSelectedPromotions] = useState<Set<number>>(new Set());

  const openArchiveWarning = () => setArchiveStep('warning');

  const proceedToArchiveForm = async () => {
    setArchiveLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/putt/archive/preview`, { credentials: 'include' });
      if (res.ok) setArchivePreview(await res.json());
    } catch (e) {
      console.error('Failed to load archive preview', e);
    } finally {
      setArchiveLoading(false);
    }
    setArchiveStep('form');
  };

  const cancelArchive = () => {
    setArchiveStep('idle');
    setArchiveSeasonName('');
    setArchivePreview(null);
    setTiedLeaders([]);
    setSelectedPromotions(new Set());
  };

  // Submit the archive. When tieResolution is provided (even an empty array),
  // it is sent as the admin's resolution of an Am-promotion tie.
  const submitArchive = async (tieResolution?: number[]) => {
    if (!archiveSeasonName.trim()) return;
    setArchiveLoading(true);
    try {
      const body: { season_name: string; tie_resolution?: number[] } = {
        season_name: archiveSeasonName.trim(),
      };
      if (tieResolution !== undefined) body.tie_resolution = tieResolution;

      const res = await fetch(`${API_BASE_URL}/api/putt/archive`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(body),
      });

      if (res.ok) {
        alert(`Season "${archiveSeasonName.trim()}" archived successfully.`);
        cancelArchive();
        return;
      }

      const err = await res.json();
      // Am-promotion tie: backend needs the admin to choose who to promote.
      if (res.status === 409 && err.error === 'am_promotion_tie') {
        setTiedLeaders(err.tied_leaders || []);
        setSelectedPromotions(new Set());
        setArchiveStep('tie');
        return;
      }
      alert(err.error || 'Archive failed.');
    } catch (e) {
      console.error('Archive error', e);
      alert('Archive failed.');
    } finally {
      setArchiveLoading(false);
    }
  };

  const performArchive = () => submitArchive();

  const togglePromotion = (playerId: number) => {
    setSelectedPromotions((prev) => {
      const next = new Set(prev);
      if (next.has(playerId)) next.delete(playerId);
      else next.add(playerId);
      return next;
    });
  };

  const confirmTieResolution = () => submitArchive(Array.from(selectedPromotions));

  const savePayoutDefaults = () => {
    localStorage.setItem(PAYOUT_DEFAULTS_KEY, JSON.stringify(payoutSettings));
    alert('Payout settings saved as default.');
  };

  const resetPayoutDefaults = () => {
    localStorage.removeItem(PAYOUT_DEFAULTS_KEY);
    setPayoutSettings({ ...FACTORY_PAYOUT_DEFAULTS });
  };

  useEffect(() => {
    if (currentUser.role === 'Admin') {
      fetchUsers();
    }
    if (currentUser.role === 'Admin' || currentUser.role === 'Director') {
      fetchTournaments();
    }
  }, [currentUser.role]);

  const fetchUsers = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/users`, {
        credentials: 'include'
      });
      if (response.ok) {
        const data = await response.json();
        setUsers(data);
      }
    } catch (error) {
      console.error('Failed to fetch users:', error);
    }
  };

  const fetchTournaments = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/putt/tournaments`, {
        credentials: 'include'
      });
      if (response.ok) {
        const data = await response.json();
        setTournaments(data.filter((t: Tournament) => t.status === 'In_Progress'));
      }
    } catch (error) {
      console.error('Failed to fetch tournaments:', error);
    }
  };

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/users`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(formData)
      });
      
      if (response.ok) {
        setFormData({ username: '', password: '', role: 'Director' });
        setShowCreateForm(false);
        fetchUsers();
      } else {
        const error = await response.json();
        alert(error.error);
      }
    } catch (error) {
      console.error('Failed to create user:', error);
    }
  };

  const handleUpdateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingUser) return;

    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/users/${editingUser.user_id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(formData)
      });
      
      if (response.ok) {
        setEditingUser(null);
        setFormData({ username: '', password: '', role: 'Director' });
        fetchUsers();
      } else {
        const error = await response.json();
        alert(error.error);
      }
    } catch (error) {
      console.error('Failed to update user:', error);
    }
  };

  const handleDeleteUser = async (userId: number) => {
    if (!window.confirm('Are you sure you want to delete this user?')) return;

    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/users/${userId}`, {
        method: 'DELETE',
        credentials: 'include'
      });
      
      if (response.ok) {
        fetchUsers();
      } else {
        const error = await response.json();
        alert(error.error);
      }
    } catch (error) {
      console.error('Failed to delete user:', error);
    }
  };

  const startEdit = (user: User) => {
    setEditingUser(user);
    setFormData({ username: user.username, password: '', role: user.role });
  };

  const handleResetData = async () => {
    const confirmation = window.prompt(
      'This will DELETE ALL tournament data, players, matches, and ace pot records. Type "RESET" to confirm:'
    );
    
    if (confirmation !== 'RESET') return;

    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/reset-data`, {
        method: 'DELETE',
        credentials: 'include'
      });
      
      if (response.ok) {
        alert('All data has been reset successfully');
      } else {
        const error = await response.json();
        alert(error.error);
      }
    } catch (error) {
      console.error('Failed to reset data:', error);
    }
  };

  return (
    <div className="admin-container">
      <div className="admin-tabs" role="tablist" aria-label="Admin sections">
        <button
          role="tab"
          aria-selected={activeAdminTab === 'users'}
          className={activeAdminTab === 'users' ? 'active' : ''}
          onClick={() => setActiveAdminTab('users')}
        >
          User Management
        </button>
        {(currentUser.role === 'Admin' || currentUser.role === 'Director') && (
          <button
            role="tab"
            aria-selected={activeAdminTab === 'tournaments'}
            className={activeAdminTab === 'tournaments' ? 'active' : ''}
            onClick={() => setActiveAdminTab('tournaments')}
          >
            Tournament Edit
          </button>
        )}
        {(currentUser.role === 'Admin' || currentUser.role === 'Director') && (
          <button
            role="tab"
            aria-selected={activeAdminTab === 'payout'}
            className={activeAdminTab === 'payout' ? 'active' : ''}
            onClick={() => setActiveAdminTab('payout')}
          >
            Season Management
          </button>
        )}
        {currentUser.role === 'Admin' && (
          <button
            role="tab"
            aria-selected={activeAdminTab === 'audit'}
            className={activeAdminTab === 'audit' ? 'active' : ''}
            onClick={() => setActiveAdminTab('audit')}
          >
            Tournament Audit
          </button>
        )}
      </div>

      {activeAdminTab === 'users' && (
        <div className="users-management">
          <h2>User Management</h2>
          
          {currentUser.role === 'Admin' && (
            <div className="admin-actions">
              <button onClick={() => setShowCreateForm(true)} className="create-button">
                Create New User
              </button>
              <button onClick={handleResetData} className="reset-button">
                Reset All Data
              </button>
            </div>
          )}

          {showCreateForm && (
            <div className="user-form">
              <h3>Create New User</h3>
              <form onSubmit={handleCreateUser}>
                <label htmlFor="create-username">Username</label>
                <input
                  id="create-username"
                  type="text"
                  placeholder="Username"
                  value={formData.username}
                  onChange={(e) => setFormData({...formData, username: e.target.value})}
                  required
                />
                <label htmlFor="create-password">Password</label>
                <input
                  id="create-password"
                  type="password"
                  placeholder="Password"
                  value={formData.password}
                  onChange={(e) => setFormData({...formData, password: e.target.value})}
                  required
                />
                <label htmlFor="create-role">Role</label>
                <select
                  id="create-role"
                  value={formData.role}
                  onChange={(e) => setFormData({...formData, role: e.target.value})}
                >
                  <option value="Director">Director</option>
                  <option value="Admin">Admin</option>
                </select>
                <div className="form-buttons">
                  <button type="submit">Create</button>
                  <button type="button" onClick={() => setShowCreateForm(false)}>Cancel</button>
                </div>
              </form>
            </div>
          )}

          {editingUser && (
            <div className="user-form">
              <h3>Edit User</h3>
              <form onSubmit={handleUpdateUser}>
                <label htmlFor="edit-username">Username</label>
                <input
                  id="edit-username"
                  type="text"
                  placeholder="Username"
                  value={formData.username}
                  onChange={(e) => setFormData({...formData, username: e.target.value})}
                  required
                />
                <label htmlFor="edit-password">New Password (leave blank to keep current)</label>
                <input
                  id="edit-password"
                  type="password"
                  placeholder="New Password (leave blank to keep current)"
                  value={formData.password}
                  onChange={(e) => setFormData({...formData, password: e.target.value})}
                />
                {currentUser.role === 'Admin' && (
                  <>
                    <label htmlFor="edit-role">Role</label>
                    <select
                      id="edit-role"
                      value={formData.role}
                      onChange={(e) => setFormData({...formData, role: e.target.value})}
                    >
                      <option value="Director">Director</option>
                      <option value="Admin">Admin</option>
                    </select>
                  </>
                )}
                <div className="form-buttons">
                  <button type="submit">Update</button>
                  <button type="button" onClick={() => setEditingUser(null)}>Cancel</button>
                </div>
              </form>
            </div>
          )}

          <div className="users-table">
            <table>
              <thead>
                <tr>
                  <th>Username</th>
                  <th>Role</th>
                  <th>Created</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {currentUser.role === 'Admin' ? users.map(user => (
                  <tr key={user.user_id}>
                    <td>{user.username}</td>
                    <td>{user.role}</td>
                    <td>{new Date(user.created_at).toLocaleDateString()}</td>
                    <td>
                      <button onClick={() => startEdit(user)} className="edit-button">Edit</button>
                      {user.user_id !== currentUser.user_id && (
                        <button onClick={() => handleDeleteUser(user.user_id)} className="delete-button">Delete</button>
                      )}
                    </td>
                  </tr>
                )) : (
                  <tr>
                    <td>{currentUser.username}</td>
                    <td>{currentUser.role}</td>
                    <td>-</td>
                    <td>
                      <button onClick={() => startEdit(currentUser as User)} className="edit-button">Edit Profile</button>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {activeAdminTab === 'tournaments' && (currentUser.role === 'Admin' || currentUser.role === 'Director') && (
        <div className="tournament-edit-section">
          {selectedTournamentId ? (
            <TournamentEdit 
              tournamentId={selectedTournamentId} 
              onBack={() => setSelectedTournamentId(null)} 
            />
          ) : (
            <div>
              <h2>Select Tournament to Edit</h2>
              <div className="tournament-list">
                {tournaments.length === 0 ? (
                  <p>No in-progress tournaments available for editing.</p>
                ) : (
                  tournaments.map(tournament => (
                    <button
                      key={tournament.tournament_id}
                      type="button"
                      className="tournament-item"
                      onClick={() => setSelectedTournamentId(tournament.tournament_id)}
                    >
                      <h3>Tournament {tournament.tournament_id}</h3>
                      <p>Date: {new Date(tournament.tournament_date).toLocaleDateString()}</p>
                      <p>Status: {tournament.status}</p>
                      <p>Teams: {tournament.total_teams}</p>
                    </button>
                  ))
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {activeAdminTab === 'audit' && currentUser.role === 'Admin' && (
        <AdminAudit user={currentUser} />
      )}

      {activeAdminTab === 'payout' && (currentUser.role === 'Admin' || currentUser.role === 'Director') && (
        <div className="payout-settings">
          {currentUser.role === 'Admin' && (
            <div className="archive-section">
              <h2>Archive Season</h2>
              <p className="payout-description">
                Archiving ends the current season, resets seasonal stats, and prepares the system for a new season. This action cannot be undone.
              </p>
              <button className="archive-button" onClick={openArchiveWarning}>Archive Season</button>

              {archiveStep === 'warning' && (
                <div className="modal-overlay" role="presentation" onClick={cancelArchive}>
                  <div
                    className="modal"
                    role="dialog"
                    aria-modal="true"
                    aria-labelledby="archive-warning-title"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <h3 id="archive-warning-title"><span aria-hidden="true">⚠️ </span>Warning</h3>
                    <p>The Archive action is <strong>destructive and cannot be reversed</strong>. It will reset all seasonal data, prune inactive players, and collapse the ace pot history.</p>
                    <p>Are you sure you want to continue?</p>
                    <div className="modal-buttons">
                      <button onClick={proceedToArchiveForm} disabled={archiveLoading}>Continue</button>
                      <button onClick={cancelArchive}>Cancel</button>
                    </div>
                  </div>
                </div>
              )}

              {archiveStep === 'form' && (
                <div className="modal-overlay" role="presentation" onClick={archiveLoading ? undefined : cancelArchive}>
                  <div
                    className="modal"
                    role="dialog"
                    aria-modal="true"
                    aria-labelledby="archive-form-title"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <h3 id="archive-form-title">Archive Season</h3>
                    {archivePreview && (
                      <table className="payout-preview-table">
                        <tbody>
                          <tr><td>Season Start</td><td>{archivePreview.start_date ?? '—'}</td></tr>
                          <tr><td>Season End</td><td>{archivePreview.end_date ?? '—'}</td></tr>
                          <tr><td>Events (Completed, to archive)</td><td>{archivePreview.event_count}</td></tr>
                          <tr><td>Unique Participants</td><td>{archivePreview.unique_participants}</td></tr>
                          <tr><td>Total Participations</td><td>{archivePreview.total_participants}</td></tr>
                        </tbody>
                      </table>
                    )}
                    {archivePreview && archivePreview.incomplete_to_delete.length > 0 && (
                      <div className="archive-warning-block">
                        <p><strong>⚠️ {archivePreview.incomplete_to_delete.length} incomplete tournament(s) will be permanently DELETED:</strong></p>
                        <ul>
                          {archivePreview.incomplete_to_delete.map((t) => (
                            <li key={t.tournament_id}>
                              Tournament {t.tournament_id} ({t.status}) — {t.tournament_date}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {archivePreview && archivePreview.am_leaders.length > 0 && (
                      <div className="archive-info-block">
                        <p><strong>Am division point leader{archivePreview.am_leaders.length > 1 ? 's' : ''}:</strong></p>
                        <ul>
                          {archivePreview.am_leaders.map((p) => (
                            <li key={p.player_id}>{p.player_name} — {p.seasonal_points} pts</li>
                          ))}
                        </ul>
                        {archivePreview.am_promotion_tie ? (
                          <p className="archive-tie-note">Multiple players are tied — you will be asked to choose who to promote.</p>
                        ) : (
                          <p>This player will be promoted Am → Pro.</p>
                        )}
                      </div>
                    )}
                    {archivePreview && !archivePreview.can_archive && (
                      <p className="archive-tie-note">No completed tournaments to archive.</p>
                    )}
                    <div className="form-section">
                      <label htmlFor="archive-season-name">Season Name:</label>
                      <input
                        id="archive-season-name"
                        type="text"
                        placeholder="e.g. Spring 2026"
                        value={archiveSeasonName}
                        onChange={(e) => setArchiveSeasonName(e.target.value)}
                      />
                    </div>
                    <div className="modal-buttons">
                      <button
                        onClick={performArchive}
                        disabled={
                          archiveLoading ||
                          !archiveSeasonName.trim() ||
                          (archivePreview != null && !archivePreview.can_archive)
                        }
                      >
                        {archiveLoading ? 'Archiving...' : 'Perform Archive'}
                      </button>
                      <button onClick={cancelArchive} disabled={archiveLoading}>Cancel</button>
                    </div>
                  </div>
                </div>
              )}

              {archiveStep === 'tie' && (
                <div className="modal-overlay" role="presentation" onClick={archiveLoading ? undefined : cancelArchive}>
                  <div
                    className="modal"
                    role="dialog"
                    aria-modal="true"
                    aria-labelledby="archive-tie-title"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <h3 id="archive-tie-title">Resolve Am Promotion Tie</h3>
                    <p>
                      The following Am players are tied for the season points lead. Select which, if any,
                      should be promoted Am → Pro. You may select none.
                    </p>
                    <ul className="tie-leader-list">
                      {tiedLeaders.map((p) => (
                        <li key={p.player_id}>
                          <label>
                            <input
                              type="checkbox"
                              checked={selectedPromotions.has(p.player_id)}
                              onChange={() => togglePromotion(p.player_id)}
                            />
                            {' '}{p.player_name} — {p.seasonal_points} pts
                          </label>
                        </li>
                      ))}
                    </ul>
                    <div className="modal-buttons">
                      <button onClick={confirmTieResolution} disabled={archiveLoading}>
                        {archiveLoading
                          ? 'Archiving...'
                          : `Confirm & Archive (promote ${selectedPromotions.size})`}
                      </button>
                      <button onClick={cancelArchive} disabled={archiveLoading}>Cancel</button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          <h2>Payout Settings</h2>
          <p className="payout-description">
            These values are used as defaults when creating new tournaments. They can be overridden per-tournament on the creation screen.
          </p>

          <div className="form-section">
            <label htmlFor="buy-in-per-player">Buy-in per Player ($):</label>
            <input
              id="buy-in-per-player"
              type="number"
              min="0"
              step="0.25"
              value={payoutSettings.buy_in_per_player}
              onChange={(e) => setPayoutSettings({ ...payoutSettings, buy_in_per_player: parseFloat(e.target.value) || 0 })}
            />
          </div>

          <div className="form-section">
            <span className="form-section-label" id="payout-mode-label">Payout Mode:</span>
            <div className="mode-toggle" role="group" aria-labelledby="payout-mode-label">
              <button
                type="button"
                aria-pressed={payoutSettings.mode === 'fixed'}
                className={payoutSettings.mode === 'fixed' ? 'active' : ''}
                onClick={() => setPayoutSettings({ ...payoutSettings, mode: 'fixed' })}
              >
                Fixed ($)
              </button>
              <button
                type="button"
                aria-pressed={payoutSettings.mode === 'percentage'}
                className={payoutSettings.mode === 'percentage' ? 'active' : ''}
                onClick={() => setPayoutSettings({ ...payoutSettings, mode: 'percentage' })}
              >
                Percentage (%)
              </button>
            </div>
          </div>

          <div className="form-section">
            <label htmlFor="second-place-value">
              2nd Place Payout ({payoutSettings.mode === 'fixed' ? '$' : '%'}):
            </label>
            <input
              id="second-place-value"
              type="number"
              min="0"
              step={payoutSettings.mode === 'fixed' ? '1' : '1'}
              max={payoutSettings.mode === 'percentage' ? '100' : undefined}
              value={payoutSettings.second_place_value}
              onChange={(e) => setPayoutSettings({ ...payoutSettings, second_place_value: parseFloat(e.target.value) || 0 })}
            />
          </div>

          <div className="payout-preview">
            <h3>Preview (sample: 12 players)</h3>
            {(() => {
              const pot = payoutSettings.buy_in_per_player * 12;
              let second = payoutSettings.mode === 'fixed'
                ? payoutSettings.second_place_value
                : pot * (payoutSettings.second_place_value / 100);
              let first = pot - second;
              if (first < second) { [first, second] = [second, first]; }
              return (
                <table className="payout-preview-table">
                  <tbody>
                    <tr><td>Total pot</td><td>${pot.toFixed(2)}</td></tr>
                    <tr><td>1st place</td><td>${first.toFixed(2)}</td></tr>
                    <tr><td>2nd place</td><td>${second.toFixed(2)}</td></tr>
                  </tbody>
                </table>
              );
            })()}
          </div>

          <div className="default-actions">
            <button className="save-default-button" onClick={savePayoutDefaults}>
              Save as Default
            </button>
            {isCustomPayout && (
              <button className="reset-default-button" onClick={resetPayoutDefaults}>
                Reset to Original Default
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default Admin;
