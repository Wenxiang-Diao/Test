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
  { key: 'sleep_score', label: 'Sleep Score', suffix: '' },
  { key: 'total_sleep_minutes', label: 'Total Sleep', suffix: ' min' },
  { key: 'awake_minutes', label: 'Awake Time', suffix: ' min' },
  { key: 'light_sleep_minutes', label: 'Light Sleep', suffix: ' min' },
  { key: 'deep_sleep_minutes', label: 'Deep Sleep', suffix: ' min' },
  { key: 'sleep_efficiency', label: 'Sleep Efficiency', suffix: '%', transform: (v) => (v * 100).toFixed(0) },
  { key: 'bed_exit_count', label: 'Bed Exits', suffix: '' },
  { key: 'longest_out_of_bed_minutes', label: 'Longest Out', suffix: ' min' },
  { key: 'avg_heart_rate', label: 'Avg Heart Rate', suffix: ' bpm' },
  { key: 'avg_breathing_rate', label: 'Avg Breathing', suffix: ' /min' },
];

export default function SleepSummaryCards({ data }: Props) {
  return (
    <div className="card">
      <h3 style={{ marginBottom: 12 }}>Sleep Summary {data.summary_date ? `(${data.summary_date})` : ''}</h3>
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
