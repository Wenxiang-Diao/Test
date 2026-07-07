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

  if (loading) return <p className="loading">加载告警...</p>;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h1 style={{ margin: 0 }}>告警中心</h1>
        <Link to="/residents" className="btn-secondary" style={{ padding: '8px 16px', borderRadius: 8 }}>
          返回总览
        </Link>
      </div>

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 16, alignItems: 'center' }}>
        <span style={{ fontSize: 13, color: '#64748b' }}>等级：</span>
        {[
          { key: 'all', label: '全部' },
          { key: 'unack', label: '未确认' },
          { key: '高', label: '高' },
          { key: '中', label: '中' },
          { key: '低', label: '低' },
        ].map(({ key, label }) => (
          <button
            key={key}
            className={severityFilter === key ? 'btn-primary' : 'btn-secondary'}
            onClick={() => setSeverityFilter(key)}
          >
            {label}
          </button>
        ))}
        <span style={{ fontSize: 13, color: '#64748b', marginLeft: 8 }}>居民：</span>
        <select
          value={residentFilter}
          onChange={(e) => setResidentFilter(e.target.value)}
          style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid #cbd5e1' }}
        >
          <option value="all">全部居民</option>
          {residents.map(([id, name]) => (
            <option key={id} value={id}>{name}</option>
          ))}
        </select>
        <span style={{ fontSize: 13, color: '#64748b', marginLeft: 8 }}>时间：</span>
        <select
          value={timeRange}
          onChange={(e) => setTimeRange(e.target.value as TimeRange)}
          style={{ padding: '8px 12px', borderRadius: 8, border: '1px solid #cbd5e1' }}
        >
          <option value="all">全部时间</option>
          <option value="24h">近 24 小时</option>
          <option value="7d">近 7 天</option>
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
          {filtered.length === 0 && <p className="loading">暂无告警</p>}
        </div>

        <div className="card">
          {selected ? (
            <>
              <h3>{selected.alert_type}</h3>
              <p style={{ marginTop: 8, fontSize: 14 }}><strong>居民：</strong>{selected.resident_name}</p>
              <p style={{ fontSize: 14 }}><strong>时间：</strong>{formatTime(selected.timestamp)}</p>
              <p style={{ fontSize: 14, marginTop: 8 }}><strong>原因：</strong>{selected.reason}</p>
              <p style={{ fontSize: 14, marginTop: 8 }}><strong>建议：</strong>{selected.suggested_action}</p>
              {!selected.acknowledged && (
                <button
                  className="btn-primary"
                  style={{ marginTop: 16, width: '100%' }}
                  onClick={() => handleAck(selected.id)}
                >
                  确认告警
                </button>
              )}
              {selected.acknowledged && (
                <p style={{ marginTop: 16, color: '#22c55e', fontSize: 14 }}>✓ 已确认</p>
              )}
            </>
          ) : (
            <p style={{ color: '#64748b' }}>点击左侧告警查看详情</p>
          )}
        </div>
      </div>
    </div>
  );
}
