import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { fetchResidents, ResidentCard } from '../api/client';
import { bedStatusColor, bedStatusLabel, formatTime, riskColor, severityColor } from '../utils/format';

type Filter = 'all' | 'alerts' | 'high_risk';

export default function ResidentOverviewPage() {
  const [residents, setResidents] = useState<ResidentCard[]>([]);
  const [filter, setFilter] = useState<Filter>('all');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = () => {
    setLoading(true);
    fetchResidents()
      .then((data) => {
        setResidents(data);
        setError('');
      })
      .catch(() => {
        setError('居民数据加载失败，请稍后重试。');
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const filtered = residents.filter((r) => {
    if (filter === 'alerts') return r.active_alert_count > 0;
    if (filter === 'high_risk') return r.risk_level === '高';
    return true;
  });

  if (loading) return <p className="loading">加载中...</p>;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h1>居民总览</h1>
        <div style={{ display: 'flex', gap: 8 }}>
          {(['all', 'alerts', 'high_risk'] as Filter[]).map((f) => (
            <button
              key={f}
              className={filter === f ? 'btn-primary' : 'btn-secondary'}
              onClick={() => setFilter(f)}
            >
              {f === 'all' ? '全部' : f === 'alerts' ? '有活跃告警' : '高风险'}
            </button>
          ))}
        </div>
      </div>

      {error && <p className="error-msg">{error}</p>}

      <div className="grid-cards">
        {filtered.map((r) => (
          <Link key={r.id} to={`/residents/${r.id}/dashboard`} className="card" style={{ display: 'block' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3>{r.name}</h3>
              <span className="badge" style={{ background: bedStatusColor(r.bed_status) }}>
                {bedStatusLabel(r.bed_status)}
              </span>
            </div>
            <p style={{ fontSize: 13, color: '#64748b', marginTop: 8 }}>
              更新：{formatTime(r.last_updated)}
            </p>
            <div style={{ marginTop: 12, display: 'flex', flexWrap: 'wrap', gap: 12, fontSize: 13 }}>
              <span>告警：{r.active_alert_count} 条</span>
              {r.highest_alert_severity && (
                <span style={{ color: severityColor(r.highest_alert_severity) }}>
                  最高等级：{r.highest_alert_severity}
                </span>
              )}
              <span style={{ color: riskColor(r.risk_level) }}>风险：{r.risk_level}</span>
            </div>
          </Link>
        ))}
      </div>

      {filtered.length === 0 && !error && <p className="loading">无匹配居民</p>}

      <p className="disclaimer">本系统输出仅供护理决策参考，不构成医疗诊断。</p>
    </div>
  );
}
