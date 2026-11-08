import React, { useState, useEffect } from 'react';
import { inventory as inventoryApi } from '../services/api';
import type { Inventory } from '../types';

export default function InventoryView() {
  const [data, setData] = useState<Inventory | null>(null);
  const [loading, setLoading] = useState(true);
  const currentYear = new Date().getFullYear();

  useEffect(() => {
    inventoryApi.get(currentYear)
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [currentYear]);

  if (loading) return <div className="loading">Loading inventory...</div>;

  if (!data || data.total_tags === 0) {
    return (
      <div className="empty-state">
        <h3>No Inventory Configured</h3>
        <p>Set the total tags for the {currentYear} season to get started.</p>
        {/* TODO: Setup inventory form */}
      </div>
    );
  }

  return (
    <div className="card">
      <div className="card-header">
        <h2>Tag Inventory — {currentYear}</h2>
        {/* TODO: Edit total tags button */}
      </div>

      <div className="flex gap-2 mb-2">
        <div className="card" style={{ flex: 1, marginBottom: 0 }}>
          <p className="text-muted" style={{ margin: '0 0 4px', fontSize: '0.8rem' }}>Total Tags</p>
          <p style={{ margin: 0, fontSize: '1.5rem', fontWeight: 700 }}>{data.total_tags}</p>
        </div>
        <div className="card" style={{ flex: 1, marginBottom: 0 }}>
          <p className="text-muted" style={{ margin: '0 0 4px', fontSize: '0.8rem' }}>Available</p>
          <p style={{ margin: 0, fontSize: '1.5rem', fontWeight: 700, color: 'var(--color-success)' }}>
            {data.available_count}
          </p>
        </div>
        <div className="card" style={{ flex: 1, marginBottom: 0 }}>
          <p className="text-muted" style={{ margin: '0 0 4px', fontSize: '0.8rem' }}>Unavailable</p>
          <p style={{ margin: 0, fontSize: '1.5rem', fontWeight: 700, color: 'var(--color-warning)' }}>
            {data.unavailable_tags.length}
          </p>
        </div>
      </div>

      {data.unavailable_tags.length > 0 && (
        <div className="mt-2">
          <h3 style={{ fontFamily: 'var(--font-body)', fontSize: '0.9rem', color: 'var(--color-text-muted)' }}>
            Unavailable Tags
          </h3>
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Tag #</th>
                  <th>Reason</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {data.unavailable_tags.map(t => (
                  <tr key={t.tag_number}>
                    <td><span className="tag-number">{t.tag_number}</span></td>
                    <td className="text-muted">{t.reason || '—'}</td>
                    <td>{/* TODO: Restore button */}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
