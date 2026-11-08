import { useState, type FormEvent } from 'react';
import { useAuth } from '../auth/AuthContext';

/**
 * Shared login modal, owned by the shell (replaces each app's bespoke login).
 * Uses AuthContext.login, which posts to /api/auth/login and refreshes the
 * three-tier identity on success.
 */
export default function LoginModal({ onClose }: { onClose: () => void }) {
  const { login } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    const res = await login(username, password);
    setLoading(false);
    if (res.ok) {
      onClose();
    } else {
      setError(res.error || 'Login failed');
    }
  };

  return (
    <div className="dgr-login-overlay" onClick={onClose}>
      <div
        className="dgr-login-modal"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label="Log in"
      >
        <h2>Log in</h2>
        <form onSubmit={handleSubmit}>
          <div className="dgr-form-group">
            <label htmlFor="dgr-username">Username</label>
            <input
              id="dgr-username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              autoComplete="username"
            />
          </div>
          <div className="dgr-form-group">
            <label htmlFor="dgr-password">Password</label>
            <input
              id="dgr-password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
            />
          </div>
          {error && <div className="dgr-error" role="alert">{error}</div>}
          <div className="dgr-modal-buttons">
            <button type="button" onClick={onClose}>Cancel</button>
            <button type="submit" disabled={loading}>
              {loading ? 'Logging in…' : 'Log in'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
