import { useCallback, useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { fetchReport, ReportData } from '../api/client';
import WeeklyTrendCharts from '../components/WeeklyTrendCharts';

function addDays(dateStr: string, delta: number): string {
  const d = new Date(dateStr + 'T12:00:00');
  d.setDate(d.getDate() + delta);
  return d.toISOString().slice(0, 10);
}

export default function ReportPage() {
  const { residentId } = useParams<{ residentId: string }>();
  const [report, setReport] = useState<ReportData | null>(null);
  const [view, setView] = useState<'daily' | 'weekly'>('daily');
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const loadReport = useCallback((date?: string) => {
    if (!residentId) return;
    setLoading(true);
    fetchReport(residentId, date)
      .then((data) => {
        setReport(data);
        if (!date && data.daily) setSelectedDate(data.daily.date);
        else if (date) setSelectedDate(date);
      })
      .finally(() => setLoading(false));
  }, [residentId]);

  useEffect(() => {
    loadReport();
  }, [loadReport]);

  const shiftDate = (delta: number) => {
    if (!selectedDate) return;
    loadReport(addDays(selectedDate, delta));
  };

  if (loading && !report) return <p className="loading">Loading report...</p>;
  if (!report) return <p className="loading">Unable to load report</p>;

  const daily = report.daily;

  return (
    <div className="report-page">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 12 }}>
        <div>
          <Link to={`/residents/${residentId}/dashboard`} style={{ color: '#2563eb', fontSize: 14 }}>
            ← Back to Dashboard
          </Link>
          <h1 style={{ marginTop: 8 }}>{report.resident_name} · Sleep Report</h1>
        </div>
        <button type="button" className="btn-secondary" onClick={() => window.print()}>
          Print / Export
        </button>
      </div>

      <div style={{ display: 'flex', gap: 8, margin: '16px 0' }}>
        <button className={view === 'daily' ? 'btn-primary' : 'btn-secondary'} onClick={() => setView('daily')}>
          Daily
        </button>
        <button className={view === 'weekly' ? 'btn-primary' : 'btn-secondary'} onClick={() => setView('weekly')}>
          Weekly
        </button>
      </div>

      {view === 'daily' && (
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
            <button type="button" className="btn-secondary" onClick={() => shiftDate(-1)} disabled={!selectedDate}>
              ◀
            </button>
            <h3 style={{ margin: 0 }}>Date: {selectedDate ?? '-'}</h3>
            <button type="button" className="btn-secondary" onClick={() => shiftDate(1)} disabled={!selectedDate}>
              ▶
            </button>
          </div>
          {daily ? (
            <div className="metric-grid">
              {[
                ['Sleep Score', daily.sleep_score],
                ['Sleep Duration', `${daily.total_sleep_minutes} min`],
                ['Awake Time', `${daily.awake_minutes} min`],
                ['Sleep Efficiency', `${(daily.sleep_efficiency * 100).toFixed(0)}%`],
                ['Bed Exits', `${daily.bed_exit_count}`],
                ['Longest Out of Bed', `${daily.longest_out_of_bed_minutes} min`],
                ['Avg Heart Rate', `${daily.avg_heart_rate} bpm`],
                ['Avg Breathing', `${daily.avg_breathing_rate} /min`],
              ].map(([label, val]) => (
                <div key={label as string} className="metric-item">
                  <div className="label">{label}</div>
                  <div className="value">{val}</div>
                </div>
              ))}
            </div>
          ) : (
            <p style={{ color: '#64748b' }}>No sleep summary data for this date</p>
          )}
        </div>
      )}

      {view === 'weekly' && (
        <div className="card">
          <h3 style={{ marginBottom: 16 }}>Last 7 days trend (with 30-day baseline)</h3>
          <WeeklyTrendCharts weekly={report.weekly} />
        </div>
      )}

      <p className="disclaimer">{report.disclaimer}</p>
    </div>
  );
}
