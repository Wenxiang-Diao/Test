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
        setError('Failed to load residents. Please try again.');
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const filtered = residents.filter((r) => {
    if (filter === 'alerts') return r.active_alert_count > 0;
    if (filter === 'high_risk') return r.risk_level === 'High';
    return true;
  });

  if (loading) return <p className="loading">Loading...</p>;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h1>Resident Overview</h1>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <Link to="/residents/manage" className="btn-secondary">Manage Residents</Link>
          {([
            ['all', 'All'],
            ['alerts', 'Active Alerts'],
            ['high_risk', 'High Risk'],
          ] as [Filter, string][]).map(([f, label]) => (
            <button
              key={f}
              className={filter === f ? 'btn-primary' : 'btn-secondary'}
              onClick={() => setFilter(f)}
            >
              {label}
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
              Updated: {formatTime(r.last_updated)}
            </p>
            <p style={{ fontSize: 13, color: '#64748b', marginTop: 4 }}>
              Location: {r.building || '-'} {r.floor_level ? `Floor ${r.floor_level}` : ''} {r.room_number ? `Room ${r.room_number}` : ''}
            </p>
            <div style={{ marginTop: 12, display: 'flex', flexWrap: 'wrap', gap: 12, fontSize: 13 }}>
              <span>Status: {r.monitoring_status}</span>
              <span>Alerts: {r.active_alert_count}</span>
              {r.highest_alert_severity && (
                <span style={{ color: severityColor(r.highest_alert_severity) }}>
                  Highest: {r.highest_alert_severity}
                </span>
              )}
              <span style={{ color: riskColor(r.risk_level) }}>Risk: {r.risk_level}</span>
            </div>
          </Link>
        ))}
      </div>

      {filtered.length === 0 && !error && <p className="loading">No matching residents</p>}

      <p className="disclaimer">System output is for care decision support only and is not a medical diagnosis.</p>
    </div>
  );
}
