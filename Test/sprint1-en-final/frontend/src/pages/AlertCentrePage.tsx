import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { acknowledgeAlert, fetchAlerts, AlertItem } from '../api/client';
import { formatTime, severityColor } from '../utils/format';

type TimeRange = 'all' | '24h' | '7d';

export default function AlertCentrePage() {
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [selected, setSelected] = useState<AlertItem | null>(null);
  const [severityFilter, setSeverityFilter] = useState<string>('all');
  const [residentFilter, setResidentFilter] = useState<string>('all');
  const [timeRange, setTimeRange] = useState<TimeRange>('all');
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    fetchAlerts()
      .then(setAlerts)
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const residents = useMemo(() => {
    const map = new Map<string, string>();
    alerts.forEach((a) => map.set(a.resident_id, a.resident_name));
    return Array.from(map.entries()).sort(([a], [b]) => a.localeCompare(b));
  }, [alerts]);

  const filtered = alerts.filter((a) => {
    if (severityFilter === 'unack' && a.acknowledged) return false;
    if (severityFilter !== 'all' && severityFilter !== 'unack' && a.severity !== severityFilter) return false;
    if (residentFilter !== 'all' && a.resident_id !== residentFilter) return false;
    if (timeRange !== 'all') {
      const ts = new Date(a.timestamp).getTime();
      const now = Date.now();
      const hours = timeRange === '24h' ? 24 : 24 * 7;
      if (now - ts > hours * 3600 * 1000) return false;
    }
    return true;
  });

  const handleAck = async (id: number) => {
    await acknowledgeAlert(id);
    load();
    setSelected(null);
  };

  if (loading) return <p className="loading">Loading alerts...</p>;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h1 style={{ margin: 0 }}>Alert Centre</h1>
        <Link to="/residents" className="btn-secondary" style={{ padding: '8px 16px', borderRadius: 8 }}>
          Back to Overview
        </Link>
      </div>

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 16, alignItems: 'center' }}>
        <span style={{ fontSize: 13, color: '#64748b' }}>Severity:</span>
        {[
          { key: 'all', label: 'All' },
          { key: 'unack', label: 'Unacknowledged' },
          { key: 'High', label: 'High' },
          { key: 'Medium', label: 'Medium' },
          { key: 'Low', label: 'Low' },
        ].map(({ key, label }) => (
          <button
            key={key}
            className={severityFilter === key ? 'btn-primary' : 'btn-secondary'}
            onClick={() => setSeverityFilter(key)}
          >
            {label}
          </button>
        ))}
        <span style={{ fontSize: 13, color: '#64748b', marginLeft: 8 }}>Resident:</span>
        <select
          value={residentFilter}
          onChange={(e) => setResidentFilter(e.target.value)}
          style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid #cbd5e1' }}
        >
          <option value="all">All residents</option>
          {residents.map(([id, name]) => (
            <option key={id} value={id}>{name}</option>
          ))}
        </select>
        <span style={{ fontSize: 13, color: '#64748b', marginLeft: 8 }}>Time:</span>
        <select
          value={timeRange}
          onChange={(e) => setTimeRange(e.target.value as TimeRange)}
          style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid #cbd5e1' }}
        >
          <option value="all">All time</option>
          <option value="24h">Last 24 hours</option>
          <option value="7d">Last 7 days</option>
        </select>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 320px', gap: 16 }}>
        <div className="card" style={{ padding: 0 }}>
          {filtered.map((a) => (
            <div
              key={a.id}
              onClick={() => setSelected(a)}
              style={{
                padding: '14px 16px', borderBottom: '1px solid #e2e8f0', cursor: 'pointer',
                background: selected?.id === a.id ? '#f1f5f9' : 'white',
                opacity: a.acknowledged ? 0.6 : 1,
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                <span className="badge" style={{ background: severityColor(a.severity) }}>{a.severity}</span>
                <strong>{a.alert_type}</strong>
                <span style={{ color: '#64748b', fontSize: 13 }}>{a.resident_name}</span>
                <span style={{ marginLeft: 'auto', fontSize: 12, color: '#94a3b8' }}>{formatTime(a.timestamp)}</span>
              </div>
              <p style={{ fontSize: 13, color: '#475569', marginTop: 4 }}>{a.reason}</p>
            </div>
          ))}
          {filtered.length === 0 && <p className="loading">No alerts</p>}
        </div>

        <div className="card">
          {selected ? (
            <>
              <h3>{selected.alert_type}</h3>
              <p style={{ marginTop: 8, fontSize: 14 }}><strong>Resident:</strong> {selected.resident_name}</p>
              <p style={{ fontSize: 14 }}><strong>Time:</strong> {formatTime(selected.timestamp)}</p>
              <p style={{ fontSize: 14, marginTop: 8 }}><strong>Reason:</strong> {selected.reason}</p>
              <p style={{ fontSize: 14, marginTop: 8 }}><strong>Suggested action:</strong> {selected.suggested_action}</p>
              {!selected.acknowledged && (
                <button
                  className="btn-primary"
                  style={{ marginTop: 16, width: '100%' }}
                  onClick={() => handleAck(selected.id)}
                >
                  Acknowledge Alert
                </button>
              )}
              {selected.acknowledged && (
                <p style={{ marginTop: 16, color: '#22c55e', fontSize: 14 }}>✓ Acknowledged</p>
              )}
            </>
          ) : (
            <p style={{ color: '#64748b' }}>Select an alert to view details</p>
          )}
        </div>
      </div>
    </div>
  );
}
