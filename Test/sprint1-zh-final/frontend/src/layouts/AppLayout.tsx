import { Outlet, Link, useNavigate } from 'react-router-dom';
import { clearToken } from '../api/client';

export default function AppLayout() {
  const navigate = useNavigate();

  const logout = () => {
    clearToken();
    navigate('/login');
  };

  return (
    <div>
      <header style={{
        background: '#1e293b', color: 'white', padding: '12px 24px',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      }}>
        <Link to="/residents" style={{ fontWeight: 700, fontSize: 18 }}>
          睡眠监测仪表盘
        </Link>
        <nav style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
          <Link to="/residents">居民总览</Link>
          <Link to="/alerts">告警中心</Link>
          <button className="btn-secondary" onClick={logout}>退出</button>
        </nav>
      </header>
      <main style={{ maxWidth: 1200, margin: '0 auto', padding: 24 }}>
        <Outlet />
      </main>
    </div>
  );
}
