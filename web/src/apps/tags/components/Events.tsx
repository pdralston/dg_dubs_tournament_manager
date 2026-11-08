import React, { useState, useEffect } from 'react';
import { events as eventsApi } from '../services/api';
import type { TagEvent } from '../types';

export default function Events() {
  const [data, setData] = useState<TagEvent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    eventsApi.list()
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="loading">Loading events...</div>;

  if (data.length === 0) {
    return (
      <div className="empty-state">
        <h3>No Events</h3>
        <p>Events will appear here once created by an admin or tournament director.</p>
      </div>
    );
  }

  const statusLabel = (status: string) => {
    switch (status) {
      case 'pending': return <span className="badge badge-pending">Pending</span>;
      case 'scheduled': return <span className="badge badge-scheduled">Scheduled</span>;
      case 'in_progress': return <span className="badge badge-in-progress">In Progress</span>;
      case 'complete': return <span className="badge badge-complete">Complete</span>;
      default: return <span className="badge">{status}</span>;
    }
  };

  return (
    <div className="card">
      <div className="card-header">
        <h2>Events</h2>
        {/* TODO: Create Event button for directors */}
      </div>
      <div className="table-container">
        <table>
          <thead>
            <tr>
              <th>Date</th>
              <th>Type</th>
              <th>Course</th>
              <th>Status</th>
              <th>Players</th>
            </tr>
          </thead>
          <tbody>
            {data.map(event => (
              <tr key={event.event_id}>
                <td>{new Date(event.date).toLocaleDateString()}</td>
                <td style={{ textTransform: 'capitalize' }}>{event.event_type}</td>
                <td>{event.course || '—'}</td>
                <td>{statusLabel(event.status)}</td>
                <td>{event.participant_count ?? 0}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
