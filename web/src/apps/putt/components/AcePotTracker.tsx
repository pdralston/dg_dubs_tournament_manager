import React, { useState, useEffect } from 'react';
import { API_BASE_URL } from '../config/api';

interface AcePotEntry {
  ace_pot_id: number;
  tournament_id?: number;
  date: string;
  description: string;
  amount: number;
}

const AcePotTracker: React.FC = () => {
  const [entries, setEntries] = useState<AcePotEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [currentTotal, setCurrentTotal] = useState(0);

  useEffect(() => {
    fetchAcePotEntries();
  }, []);

  const fetchAcePotEntries = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/putt/ace-pot`, { credentials: 'include' });
      if (response.ok) {
        const data = await response.json();
        setEntries(data);
        
        // Calculate current total
        const total = data.reduce((sum: number, entry: AcePotEntry) => sum + entry.amount, 0);
        setCurrentTotal(total);
      }
    } catch (error) {
      console.error('Failed to fetch ace pot entries:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div className="loading">Loading ace pot...</div>;

  return (
    <div className="ace-pot-tracker">
      <div className="page-header">
        <h2>Ace Pot Tracker</h2>
        <div className="current-total">
          Current Total: <span className="amount">${currentTotal.toFixed(2)}</span>
        </div>
      </div>
      
      <div className="table-container">
        <table className="ace-pot-table">
          <thead>
            <tr>
              <th>Date</th>
              <th>Description</th>
              <th>Amount</th>
              <th>Running Total</th>
            </tr>
          </thead>
          <tbody>
            {entries.map((entry, index) => {
              const runningTotal = entries
                .slice(0, index + 1)
                .reduce((sum, e) => sum + e.amount, 0);
              
              return (
                <tr key={entry.ace_pot_id}>
                  <td>{new Date(entry.date).toLocaleDateString()}</td>
                  <td>{entry.description}</td>
                  <td className={entry.amount >= 0 ? 'positive' : 'negative'}>
                    {entry.amount >= 0 ? '+' : ''}${entry.amount.toFixed(2)}
                  </td>
                  <td className="running-total">${runningTotal.toFixed(2)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {entries.length === 0 && (
          <div className="empty-state">No ace pot entries found.</div>
        )}
      </div>
    </div>
  );
};

export default AcePotTracker;
