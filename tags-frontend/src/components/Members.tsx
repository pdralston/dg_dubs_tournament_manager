import React, { useState, useEffect } from 'react';
import { members as membersApi } from '../services/api';
import type { TagMember } from '../types';

export default function Members() {
  const [data, setData] = useState<TagMember[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    membersApi.list()
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="loading">Loading members...</div>;

  if (data.length === 0) {
    return (
      <div className="empty-state">
        <h3>No Members</h3>
        <p>Members will appear here once registered.</p>
      </div>
    );
  }

  return (
    <div className="card">
      <div className="card-header">
        <h2>Members</h2>
        {/* TODO: Add Member button, search bar */}
      </div>
      <div className="table-container">
        <table>
          <thead>
            <tr>
              <th>Tag</th>
              <th>Name</th>
              <th>UDisc</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {data.map(member => (
              <tr key={member.member_id}>
                <td>
                  {member.current_tag ? (
                    <span className="tag-number">{member.current_tag}</span>
                  ) : (
                    <span className="text-muted">—</span>
                  )}
                </td>
                <td>{member.name}</td>
                <td className="text-muted">{member.udisc_name || '—'}</td>
                <td>
                  {member.is_active ? (
                    <span className="text-success">Active</span>
                  ) : (
                    <span className="text-muted">Inactive</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
