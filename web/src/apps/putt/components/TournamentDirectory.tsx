import React, { useState, useEffect } from 'react';
import { API_BASE_URL } from '../config/api';

interface Tournament {
  tournament_id: number;
  tournament_date: string;
  status: string;
  total_teams?: number;
}

interface Season {
  season_id: number;
  season_name: string;
  start_date: string | null;
  end_date: string | null;
}

interface TournamentDirectoryProps {
  onTournamentSelect: (tournamentId: number) => void;
  onTournamentManage: (tournamentId: number) => void;
  onCreateTournament: () => void;
  onEditPending: (tournamentId: number) => void;
  // Controlled by App so the selection survives navigating into a tournament
  // and back. 'current' = active season; otherwise an archived season_id string.
  selectedSeason: string;
  onSeasonChange: (season: string) => void;
  userRole?: string;
}

const TournamentDirectory: React.FC<TournamentDirectoryProps> = ({ 
  onTournamentSelect, 
  onTournamentManage, 
  onCreateTournament,
  onEditPending,
  selectedSeason,
  onSeasonChange,
  userRole = 'Viewer'
}) => {
  const [tournaments, setTournaments] = useState<Tournament[]>([]);
  const [seasons, setSeasons] = useState<Season[]>([]);
  const [loading, setLoading] = useState(true);

  const isArchivedSeason = selectedSeason !== 'current';

  useEffect(() => {
    fetchSeasons();
  }, []);

  useEffect(() => {
    fetchTournaments(selectedSeason);
  }, [selectedSeason]);

  const fetchSeasons = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/putt/seasons`, { credentials: 'include' });
      if (response.ok) {
        const data = await response.json();
        setSeasons(data);
      }
    } catch (error) {
      console.error('Failed to fetch seasons:', error);
    }
  };

  const fetchTournaments = async (season: string) => {
    setLoading(true);
    try {
      const url = season === 'current'
        ? `${API_BASE_URL}/api/putt/tournaments`
        : `${API_BASE_URL}/api/putt/tournaments?season_id=${encodeURIComponent(season)}`;
      const response = await fetch(url, { credentials: 'include' });
      if (response.ok) {
        const data = await response.json();
        setTournaments(data);
      }
    } catch (error) {
      console.error('Failed to fetch tournaments:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (tournamentId: number, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!window.confirm('Are you sure you want to delete this tournament? This will delete all matches, teams, and registrations.')) {
      return;
    }

    try {
      const response = await fetch(`${API_BASE_URL}/api/putt/tournaments/${tournamentId}`, {
        method: 'DELETE',
        credentials: 'include'
      });

      if (response.ok) {
        setTournaments(prev => prev.filter(t => t.tournament_id !== tournamentId));
      } else {
        alert('Failed to delete tournament');
      }
    } catch (error) {
      console.error('Failed to delete tournament:', error);
      alert('Failed to delete tournament');
    }
  };

  const isAdminOrDirector = userRole === 'Admin' || userRole === 'Director';
  // Management actions (Manage / Edit / Delete) only apply to the current season.
  // Archived seasons are read-only, so only "View" is offered there.
  const showManagementActions = isAdminOrDirector && !isArchivedSeason;
  const visibleTournaments = isAdminOrDirector
    ? tournaments
    : tournaments.filter(t => t.status !== 'Pending');

  return (
    <div className="tournament-directory">
      <div className="page-header">
        <h2>Tournaments</h2>
        <div className="page-header-actions">
          <label className="season-selector">
            <span>Season:</span>
            <select
              value={selectedSeason}
              onChange={(e) => onSeasonChange(e.target.value)}
            >
              <option value="current">Current Season</option>
              {seasons.map(season => (
                <option key={season.season_id} value={String(season.season_id)}>
                  {season.season_name}
                </option>
              ))}
            </select>
          </label>
          {isAdminOrDirector && !isArchivedSeason && (
            <button className="create-tournament-button" onClick={onCreateTournament}>
              Create Tournament
            </button>
          )}
        </div>
      </div>

      {loading ? (
        <div className="loading">Loading tournaments...</div>
      ) : (
      <div className="table-container">
        <table className="tournaments-table">
          <thead>
            <tr>
              <th>Date</th>
              <th>Status</th>
              <th>Teams</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {visibleTournaments.map(tournament => (
              <tr key={tournament.tournament_id}>
                <td>{new Date(tournament.tournament_date).toLocaleDateString()}</td>
                <td>{tournament.status}</td>
                <td>{tournament.total_teams || 0}</td>
                <td>
                  <div className="action-buttons">
                    {tournament.status === 'Pending' ? (
                      showManagementActions && (
                        <button className="manage-button" onClick={() => onEditPending(tournament.tournament_id)}>
                          Edit
                        </button>
                      )
                    ) : (
                      <>
                        <button className="view-button" onClick={() => onTournamentSelect(tournament.tournament_id)}>
                          View
                        </button>
                        {showManagementActions && (
                          <button className="manage-button" onClick={() => onTournamentManage(tournament.tournament_id)}>
                            Manage
                          </button>
                        )}
                      </>
                    )}
                    {userRole === 'Admin' && !isArchivedSeason && (
                      <button className="delete-button" onClick={(e) => handleDelete(tournament.tournament_id, e)}>
                        Delete
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {visibleTournaments.length === 0 && (
          <div className="empty-state">No tournaments found.</div>
        )}
      </div>
      )}
    </div>
  );
};

export default TournamentDirectory;
