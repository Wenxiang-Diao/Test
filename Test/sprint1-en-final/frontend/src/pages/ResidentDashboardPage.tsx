import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { fetchDashboard, fetchPrediction, DashboardData, PredictionData } from '../api/client';
import StatusCard from '../components/StatusCard';
import SleepSummaryCards from '../components/SleepSummaryCards';
import BedExitTimeline from '../components/BedExitTimeline';
import VitalSignCharts from '../components/VitalSignCharts';
import PredictionPanel from '../components/PredictionPanel';

export default function ResidentDashboardPage() {
  const { id } = useParams<{ id: string }>();
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [prediction, setPrediction] = useState<PredictionData | null>(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<'overview' | 'timeline'>('overview');

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    Promise.all([fetchDashboard(id), fetchPrediction(id)])
      .then(([d, p]) => { setDashboard(d); setPrediction(p); })
      .finally(() => setLoading(false));
  }, [id]);

  if (loading || !dashboard) return <p className="loading">Loading dashboard...</p>;

  const bl = dashboard.baseline;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <div>
          <Link to="/residents" style={{ color: '#2563eb', fontSize: 14 }}>← Back to Overview</Link>
          <h1 style={{ marginTop: 4 }}>{dashboard.resident_name}</h1>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <Link to={`/reports/${id}`} className="btn-secondary" style={{ padding: '8px 16px', borderRadius: 8 }}>
            View Report
          </Link>
          <Link to="/alerts" className="btn-secondary" style={{ padding: '8px 16px', borderRadius: 8 }}>
            Alert Centre
          </Link>
        </div>
      </div>

      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        <button className={tab === 'overview' ? 'btn-primary' : 'btn-secondary'} onClick={() => setTab('overview')}>
          Dashboard Overview
        </button>
        <button className={tab === 'timeline' ? 'btn-primary' : 'btn-secondary'} onClick={() => setTab('timeline')}>
          Timeline & Prediction
        </button>
      </div>

      {tab === 'overview' ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <StatusCard data={dashboard} />
          <SleepSummaryCards data={dashboard} />
          <VitalSignCharts data={dashboard} />
          {bl && (
            <div className="card">
              <h3 style={{ marginBottom: 12 }}>Historical Comparison</h3>
              <div className="metric-grid">
                <div className="metric-item">
                  <div className="label">7-day avg sleep</div>
                  <div className="value">{bl.avg_sleep_minutes_7d?.toFixed(0) ?? '-'} min</div>
                </div>
                <div className="metric-item">
                  <div className="label">30-day avg sleep</div>
                  <div className="value">{bl.avg_sleep_minutes_30d?.toFixed(0) ?? '-'} min</div>
                </div>
                <div className="metric-item">
                  <div className="label">7-day avg efficiency</div>
                  <div className="value">
                    {bl.avg_efficiency_7d != null ? `${(bl.avg_efficiency_7d * 100).toFixed(0)}%` : '-'}
                  </div>
                </div>
                <div className="metric-item">
                  <div className="label">30-day avg efficiency</div>
                  <div className="value">
                    {bl.avg_efficiency_30d != null ? `${(bl.avg_efficiency_30d * 100).toFixed(0)}%` : '-'}
                  </div>
                </div>
                <div className="metric-item">
                  <div className="label">7-day bed exits</div>
                  <div className="value">{bl.avg_bed_exit_count_7d?.toFixed(1) ?? '-'}</div>
                </div>
                <div className="metric-item">
                  <div className="label">30-day bed exits</div>
                  <div className="value">{bl.avg_bed_exit_count_30d?.toFixed(1) ?? '-'}</div>
                </div>
              </div>
            </div>
          )}
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          <BedExitTimeline data={dashboard} />
          {prediction && <PredictionPanel data={prediction} />}
        </div>
      )}

      <p className="disclaimer">{dashboard.disclaimer}</p>
    </div>
  );
}
