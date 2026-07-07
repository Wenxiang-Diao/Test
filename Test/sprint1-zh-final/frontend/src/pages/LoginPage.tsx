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
      setError('用户名或密码错误');
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
        <h1 style={{ fontSize: 22, marginBottom: 8 }}>睡眠监测仪表盘</h1>
        <p style={{ color: '#64748b', marginBottom: 24, fontSize: 14 }}>COMP9900 决策支持原型</p>
        <label style={{ display: 'block', marginBottom: 16 }}>
          <span style={{ fontSize: 13, color: '#64748b' }}>用户名</span>
          <input
            style={{ width: '100%', marginTop: 4 }}
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />
        </label>
        <label style={{ display: 'block', marginBottom: 16 }}>
          <span style={{ fontSize: 13, color: '#64748b' }}>密码</span>
          <input
            type="password"
            style={{ width: '100%', marginTop: 4 }}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>
        {error && <p className="error-msg">{error}</p>}
        <button className="btn-primary" type="submit" style={{ width: '100%', marginTop: 8 }} disabled={loading}>
          {loading ? '登录中...' : '登录'}
        </button>
        <p className="disclaimer" style={{ marginTop: 16 }}>
          本系统输出仅供护理决策参考，不构成医疗诊断。
        </p>
      </form>
    </div>
  );
}
