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

  if (loading && !report) return <p className="loading">加载报告...</p>;
  if (!report) return <p className="loading">无法加载报告</p>;

  const daily = report.daily;

  return (
    <div className="report-page">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 12 }}>
        <div>
          <Link to={`/residents/${residentId}/dashboard`} style={{ color: '#2563eb', fontSize: 14 }}>
            ← 返回看板
          </Link>
          <h1 style={{ marginTop: 8 }}>{report.resident_name} · 睡眠报告</h1>
        </div>
        <button type="button" className="btn-secondary" onClick={() => window.print()}>
          打印 / 导出
        </button>
      </div>

      <div style={{ display: 'flex', gap: 8, margin: '16px 0' }}>
        <button className={view === 'daily' ? 'btn-primary' : 'btn-secondary'} onClick={() => setView('daily')}>
          日报
        </button>
        <button className={view === 'weekly' ? 'btn-primary' : 'btn-secondary'} onClick={() => setView('weekly')}>
          周报
        </button>
      </div>

      {view === 'daily' && (
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
            <button type="button" className="btn-secondary" onClick={() => shiftDate(-1)} disabled={!selectedDate}>
              ◀
            </button>
            <h3 style={{ margin: 0 }}>日期：{selectedDate ?? '-'}</h3>
            <button type="button" className="btn-secondary" onClick={() => shiftDate(1)} disabled={!selectedDate}>
              ▶
            </button>
          </div>
          {daily ? (
            <div className="metric-grid">
              {[
                ['睡眠评分', daily.sleep_score],
                ['睡眠时长', `${daily.total_sleep_minutes} 分`],
                ['清醒时长', `${daily.awake_minutes} 分`],
                ['睡眠效率', `${(daily.sleep_efficiency * 100).toFixed(0)}%`],
                ['离床次数', `${daily.bed_exit_count} 次`],
                ['最长离床', `${daily.longest_out_of_bed_minutes} 分`],
                ['平均心率', `${daily.avg_heart_rate} bpm`],
                ['平均呼吸', `${daily.avg_breathing_rate} 次/分`],
              ].map(([label, val]) => (
                <div key={label as string} className="metric-item">
                  <div className="label">{label}</div>
                  <div className="value">{val}</div>
                </div>
              ))}
            </div>
          ) : (
            <p style={{ color: '#64748b' }}>该日期暂无睡眠摘要数据</p>
          )}
        </div>
      )}

      {view === 'weekly' && (
        <div className="card">
          <h3 style={{ marginBottom: 16 }}>近 7 天趋势（含 30 天基线参考）</h3>
          <WeeklyTrendCharts weekly={report.weekly} />
        </div>
      )}

      <p className="disclaimer">{report.disclaimer}</p>
    </div>
  );
}
