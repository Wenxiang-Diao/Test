import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { login } from '../api/client';

export default function LoginPage() {
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('admin123');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(username, password);
      navigate('/residents');
    } catch {
      setError('Invalid username or password');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: 'linear-gradient(135deg, #1e293b 0%, #334155 100%)',
    }}>
      <form className="card" onSubmit={handleSubmit} style={{ width: 360 }}>
        <h1 style={{ fontSize: 22, marginBottom: 8 }}>Sleep Monitoring Dashboard</h1>
        <p style={{ color: '#64748b', marginBottom: 24, fontSize: 14 }}>COMP9900 Decision-Support Prototype</p>
        <label style={{ display: 'block', marginBottom: 16 }}>
          <span style={{ fontSize: 13, color: '#64748b' }}>Username</span>
          <input
            style={{ width: '100%', marginTop: 4 }}
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />
        </label>
        <label style={{ display: 'block', marginBottom: 16 }}>
          <span style={{ fontSize: 13, color: '#64748b' }}>Password</span>
          <input
            type="password"
            style={{ width: '100%', marginTop: 4 }}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>
        {error && <p className="error-msg">{error}</p>}
        <button className="btn-primary" type="submit" style={{ width: '100%', marginTop: 8 }} disabled={loading}>
          {loading ? 'Signing in...' : 'Sign In'}
        </button>
        <p className="disclaimer" style={{ marginTop: 16 }}>
          System output is for care decision support only and is not a medical diagnosis.
        </p>
      </form>
    </div>
  );
}
