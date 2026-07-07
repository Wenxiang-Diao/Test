import { DashboardData } from '../api/client';

interface Props {
  data: DashboardData;
}

interface MetricDef {
  key: keyof DashboardData;
  label: string;
  suffix: string;
  transform?: (v: number) => string;
}

const metrics: MetricDef[] = [
  { key: 'sleep_score', label: '睡眠评分', suffix: '' },
  { key: 'total_sleep_minutes', label: '睡眠时长', suffix: ' 分' },
  { key: 'sleep_efficiency', label: '睡眠效率', suffix: '%', transform: (v) => (v * 100).toFixed(0) },
  { key: 'bed_exit_count', label: '离床次数', suffix: ' 次' },
  { key: 'avg_heart_rate', label: '平均心率', suffix: ' bpm' },
  { key: 'avg_breathing_rate', label: '平均呼吸', suffix: ' 次/分' },
];

export default function SleepSummaryCards({ data }: Props) {
  return (
    <div className="card">
      <h3 style={{ marginBottom: 12 }}>睡眠摘要 {data.summary_date ? `(${data.summary_date})` : ''}</h3>
      <div className="metric-grid">
        {metrics.map(({ key, label, suffix, transform }) => {
          const raw = data[key] as number | null;
          const value = raw == null ? '-' : transform ? transform(raw) + suffix : String(raw) + suffix;
          return (
            <div key={key} className="metric-item">
              <div className="label">{label}</div>
              <div className="value">{value}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
