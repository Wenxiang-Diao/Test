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

  if (loading || !dashboard) return <p className="loading">加载看板数据...</p>;

  const bl = dashboard.baseline;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <div>
          <Link to="/residents" style={{ color: '#2563eb', fontSize: 14 }}>← 返回总览</Link>
          <h1 style={{ marginTop: 4 }}>{dashboard.resident_name}</h1>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <Link to={`/reports/${id}`} className="btn-secondary" style={{ padding: '8px 16px', borderRadius: 8 }}>
            查看报告
          </Link>
          <Link to="/alerts" className="btn-secondary" style={{ padding: '8px 16px', borderRadius: 8 }}>
            告警中心
          </Link>
        </div>
      </div>

      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        <button className={tab === 'overview' ? 'btn-primary' : 'btn-secondary'} onClick={() => setTab('overview')}>
          看板概览
        </button>
        <button className={tab === 'timeline' ? 'btn-primary' : 'btn-secondary'} onClick={() => setTab('timeline')}>
          离床时间线与预测
        </button>
      </div>

      {tab === 'overview' ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <StatusCard data={dashboard} />
          <SleepSummaryCards data={dashboard} />
          <VitalSignCharts data={dashboard} />
          {bl && (
            <div className="card">
              <h3 style={{ marginBottom: 12 }}>历史对比</h3>
              <div className="metric-grid">
                <div className="metric-item">
                  <div className="label">7天均值睡眠</div>
                  <div className="value">{bl.avg_sleep_minutes_7d?.toFixed(0) ?? '-'} 分</div>
                </div>
                <div className="metric-item">
                  <div className="label">30天均值睡眠</div>
                  <div className="value">{bl.avg_sleep_minutes_30d?.toFixed(0) ?? '-'} 分</div>
                </div>
                <div className="metric-item">
                  <div className="label">7天均值效率</div>
                  <div className="value">
                    {bl.avg_efficiency_7d != null ? `${(bl.avg_efficiency_7d * 100).toFixed(0)}%` : '-'}
                  </div>
                </div>
                <div className="metric-item">
                  <div className="label">30天均值效率</div>
                  <div className="value">
                    {bl.avg_efficiency_30d != null ? `${(bl.avg_efficiency_30d * 100).toFixed(0)}%` : '-'}
                  </div>
                </div>
                <div className="metric-item">
                  <div className="label">7天离床次数</div>
                  <div className="value">{bl.avg_bed_exit_count_7d?.toFixed(1) ?? '-'}</div>
                </div>
                <div className="metric-item">
                  <div className="label">30天离床次数</div>
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
