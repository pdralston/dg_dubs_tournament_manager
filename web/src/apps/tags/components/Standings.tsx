import React, { useState, useEffect } from 'react';
import { standings as standingsApi } from '../services/api';
import type { StandingEntry } from '../types';

export default function Standings() {
  const [data, setData] = useState<StandingEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    standingsApi.get()
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="loading">Loading standings...</div>;

  if (data.length === 0) {
    return (
      <div className="empty-state">
        <h3>No Tag Assignments Yet</h3>
        <p>Tag standings will appear here after the first event is completed.</p>
      </div>
    );
  }

  return (
    <div className="card">
      <div className="card-header">
        <h2>Current Tag Standings</h2>
      </div>
      <div className="table-container">
        <table>
          <thead>
            <tr>
              <th>Tag</th>
              <th>Name</th>
              <th>UDisc</th>
            </tr>
          </thead>
          <tbody>
            {data.map(entry => (
              <tr key={entry.member_id}>
                <td>
                  <span className={`tag-number ${entry.current_tag <= 3 ? 'tag-gold' : ''}`}>
                    {entry.current_tag}
                  </span>
                </td>
                <td>{entry.name}</td>
                <td className="text-muted">{entry.udisc_name || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
