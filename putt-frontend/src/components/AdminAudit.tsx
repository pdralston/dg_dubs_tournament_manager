import React, { useState, useEffect } from 'react';
import { API_BASE_URL } from '../config/api';

interface Tournament {
  tournament_id: number;
  tournament_date: string;
  status: string;
  ace_pot_payout: number;
}

interface Team {
  team_id: number;
  player1_id: number;
  player1_name: string;
  player2_id?: number;
  player2_name?: string;
  is_ghost_team: boolean;
  final_place?: number;
  points_earned?: number;
}

interface Match {
  match_id: number;
  stage_type: string;
  round_type: string;
  round_number: number;
  team1_id?: number;
  team2_id?: number;
  team1_score?: number;
  team2_score?: number;
  match_status: string;
}

interface AuditData {
  tournament: Tournament;
  teams: Team[];
  matches: Match[];
}

interface AdminAuditProps {
  user: { role: string };
}

const AdminAudit: React.FC<AdminAuditProps> = ({ user }) => {
  const [completedTournaments, setCompletedTournaments] = useState<Tournament[]>([]);
  const [selectedTournament, setSelectedTournament] = useState<number | null>(null);
  const [auditData, setAuditData] = useState<AuditData | null>(null);
  const [loading, setLoading] = useState(false);
  const [pendingChanges, setPendingChanges] = useState<{
    teamPlaces: { [teamId: number]: number };
  }>({ teamPlaces: {} });
  const [hasChanges, setHasChanges] = useState(false);

  useEffect(() => {
    fetchCompletedTournaments();
  }, []);

  const fetchCompletedTournaments = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/putt/tournaments`, {
        credentials: 'include'
      });
      const data = await response.json();
      const completed = data.filter((t: Tournament) => t.status === 'Completed');
      setCompletedTournaments(completed);
    } catch (error) {
      console.error('Error fetching tournaments:', error);
    }
  };

  const fetchAuditData = async (tournamentId: number) => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/putt/admin/tournaments/${tournamentId}/audit`, {
        credentials: 'include'
      });
      
      if (!response.ok) {
        console.error('API Error:', response.status, response.statusText);
        return;
      }
      
      const data = await response.json();
      console.log('Audit data received:', data);
      setAuditData(data);
    } catch (error) {
      console.error('Error fetching audit data:', error);
    }
    setLoading(false);
  };

  const updateTeamPlace = (teamId: number, finalPlace: number) => {
    setPendingChanges(prev => ({
      ...prev,
      teamPlaces: { ...prev.teamPlaces, [teamId]: finalPlace }
    }));
    setHasChanges(true);
  };

  const submitChanges = async () => {
    if (!selectedTournament || !hasChanges) return;
    
    try {
      // Submit team place changes
      for (const [teamId, finalPlace] of Object.entries(pendingChanges.teamPlaces)) {
        await fetch(`${API_BASE_URL}/api/putt/admin/tournaments/${selectedTournament}/teams/${teamId}/place`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({ final_place: finalPlace })
        });
      }

      // Reset changes and refresh data
      setPendingChanges({ teamPlaces: {} });
      setHasChanges(false);
      fetchAuditData(selectedTournament);
      alert('Changes saved successfully');
    } catch (error) {
      console.error('Error saving changes:', error);
      alert('Error saving changes');
    }
  };

  const recalculateStats = async () => {
    if (!selectedTournament) return;
    
    try {
      const response = await fetch(`${API_BASE_URL}/api/putt/admin/tournaments/${selectedTournament}/recalculate`, {
        method: 'POST',
        credentials: 'include'
      });
      
      if (response.ok) {
        fetchAuditData(selectedTournament);
        alert('Tournament stats recalculated successfully');
      }
    } catch (error) {
      console.error('Error recalculating stats:', error);
    }
  };

  const getTeamName = (team: Team) => {
    if (team.is_ghost_team) return `${team.player1_name} (Ghost)`;
    return team.player2_name ? `${team.player1_name} & ${team.player2_name}` : team.player1_name;
  };

  const getMatchTeamName = (teamId: number | undefined) => {
    if (!teamId || !auditData) return 'TBD';
    const team = auditData.teams.find(t => t.team_id === teamId);
    return team ? getTeamName(team) : 'Unknown';
  };

  if (user.role !== 'Admin') {
    return <div className="admin-audit">Access denied. Admin role required.</div>;
  }

  return (
    <div className="admin-audit">
      <h2>Tournament Audit</h2>
      
      <div className="tournament-selector">
        <label>Select Completed Tournament:</label>
        <select 
          value={selectedTournament || ''} 
          onChange={(e) => {
            const id = parseInt(e.target.value);
            setSelectedTournament(id);
            fetchAuditData(id);
          }}
        >
          <option value="">Choose tournament...</option>
          {completedTournaments.map(t => (
            <option key={t.tournament_id} value={t.tournament_id}>
              {new Date(t.tournament_date).toLocaleDateString()}
            </option>
          ))}
        </select>
      </div>

      {loading && <div>Loading audit data...</div>}

      {auditData && (
        <div className="audit-content">
          <div className="audit-header">
            <h3>Tournament: {auditData?.tournament?.tournament_date ? new Date(auditData.tournament.tournament_date).toLocaleDateString() : 'Loading...'}</h3>
            <div className="audit-actions">
              {hasChanges && (
                <button onClick={submitChanges} className="submit-changes-btn">
                  Save Changes
                </button>
              )}
              <button onClick={recalculateStats} className="recalculate-btn">
                Recalculate All Stats
              </button>
            </div>
          </div>

          <div className="audit-sections">
            <div className="teams-section">
              <h4>Final Standings</h4>
              <table className="audit-table">
                <thead>
                  <tr>
                    <th>Place</th>
                    <th>Team</th>
                    <th>Points</th>
                  </tr>
                </thead>
                <tbody>
                  {auditData.teams
                    .sort((a, b) => (a.final_place || 999) - (b.final_place || 999))
                    .map(team => (
                    <tr key={team.team_id}>
                      <td>
                        <input
                          type="number"
                          value={pendingChanges.teamPlaces[team.team_id] ?? team.final_place ?? ''}
                          onChange={(e) => updateTeamPlace(team.team_id, parseInt(e.target.value))}
                          className="place-input"
                        />
                      </td>
                      <td>{getTeamName(team)}</td>
                      <td>{team.points_earned || 0}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminAudit;
