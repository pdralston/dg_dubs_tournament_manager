import React, { useState, useEffect } from 'react';
import { API_BASE_URL } from '../config/api';
import { AcePotBalance, AcePotConfig, AcePotEntry } from '../types';

interface AcePotTrackerProps {
  userRole: string;
}

const AcePotTracker: React.FC<AcePotTrackerProps> = ({ userRole }) => {
  const [balance, setBalance] = useState<AcePotBalance | null>(null);
  const [config, setConfig] = useState<AcePotConfig | null>(null);
  const [ledger, setLedger] = useState<AcePotEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [newCap, setNewCap] = useState('');
  const [newBalance, setNewBalance] = useState('');
  const [balanceDesc, setBalanceDesc] = useState('');
  const [error, setError] = useState('');

  const canEdit = userRole === 'admin' || userRole === 'director';

  const fetchData = async () => {
    try {
      const [balRes, cfgRes, ledRes] = await Promise.all([
        fetch(`${API_BASE_URL}/api/ace-pot/balance`, { credentials: 'include' }),
        fetch(`${API_BASE_URL}/api/ace-pot/config`, { credentials: 'include' }),
        fetch(`${API_BASE_URL}/api/ace-pot/ledger`, { credentials: 'include' }),
      ]);
      if (balRes.ok) setBalance(await balRes.json());
      if (cfgRes.ok) {
        const c = await cfgRes.json();
        setConfig(c);
        setNewCap(c.cap_amount.toString());
      }
      if (ledRes.ok) setLedger(await ledRes.json());
    } catch {} finally { setLoading(false); }
  };

  useEffect(() => { fetchData(); }, []);

  const updateCap = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    const res = await fetch(`${API_BASE_URL}/api/ace-pot/config`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ cap_amount: parseFloat(newCap) })
    });
    if (res.ok) { setConfig(await res.json()); }
    else { setError('Failed to update cap'); }
  };

  const updateBalance = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    const res = await fetch(`${API_BASE_URL}/api/ace-pot/balance`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ amount: parseFloat(newBalance), description: balanceDesc || undefined })
    });
    if (res.ok) {
      setBalance(await res.json());
      setNewBalance('');
      setBalanceDesc('');
      fetchData();
    } else { setError('Failed to update balance'); }
  };

  if (loading) return <div className="loading">Loading ace pot...</div>;

  return (
    <div className="page-content">
      <h2>Ace Pot</h2>
      {error && <div className="error-message" role="alert">{error}</div>}

      {balance && (
        <div className="ace-pot-summary">
          <div className="stat-card">
            <span className="stat-label">Current Balance</span>
            <span className="stat-value">${balance.current?.toFixed(2) ?? balance.total?.toFixed(2)}</span>
          </div>
          {config && (
            <div className="stat-card">
              <span className="stat-label">Cap Amount</span>
              <span className="stat-value">${config.cap_amount.toFixed(2)}</span>
            </div>
          )}
        </div>
      )}

      {canEdit && (
        <div className="admin-controls">
          <form className="inline-form" onSubmit={updateCap}>
            <div className="form-group">
              <label htmlFor="ace-cap">Cap Amount ($):</label>
              <input id="ace-cap" type="number" step="0.01" min="0" value={newCap} onChange={e => setNewCap(e.target.value)} />
            </div>
            <button type="submit" className="action-button">Update Cap</button>
          </form>

          <form className="inline-form" onSubmit={updateBalance}>
            <div className="form-group">
              <label htmlFor="ace-bal">Set Balance ($):</label>
              <input id="ace-bal" type="number" step="0.01" min="0" value={newBalance} onChange={e => setNewBalance(e.target.value)} required />
            </div>
            <div className="form-group">
              <label htmlFor="ace-desc">Description:</label>
              <input id="ace-desc" type="text" value={balanceDesc} onChange={e => setBalanceDesc(e.target.value)} placeholder="Manual adjustment" />
            </div>
            <button type="submit" className="action-button">Set Balance</button>
          </form>
        </div>
      )}

      {ledger.length > 0 && (
        <>
          <h3>Ledger</h3>
          <table className="data-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Description</th>
                <th>Amount</th>
                <th>Balance</th>
              </tr>
            </thead>
            <tbody>
              {ledger.map(entry => (
                <tr key={entry.id}>
                  <td>{entry.date}</td>
                  <td>{entry.description}</td>
                  <td className={entry.amount >= 0 ? 'positive' : 'negative'}>
                    {entry.amount >= 0 ? '+' : ''}${entry.amount.toFixed(2)}
                  </td>
                  <td>${entry.balance.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  );
};

export default AcePotTracker;
