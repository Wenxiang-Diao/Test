import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceArea,
} from 'recharts';
import { DashboardData } from '../api/client';

interface Props {
  data: DashboardData;
}

function formatChartTime(iso: string) {
  return new Date(iso).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
}

export default function VitalSignCharts({ data }: Props) {
  const chartData = data.vital_samples.map((v) => ({
    time: formatChartTime(v.timestamp),
    hr: v.heart_rate_bpm,
    br: v.breathing_rate_per_min,
  }));

  const bl = data.baseline;

  return (
    <div className="card">
      <h3 style={{ marginBottom: 16 }}>生命体征趋势</h3>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
        <div>
          <p style={{ fontSize: 13, color: '#64748b', marginBottom: 8 }}>心率 (bpm)</p>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="time" tick={{ fontSize: 11 }} />
              <YAxis domain={['auto', 'auto']} tick={{ fontSize: 11 }} />
              <Tooltip />
              {bl?.heart_rate_baseline_low != null && bl?.heart_rate_baseline_high != null && (
                <ReferenceArea
                  y1={bl.heart_rate_baseline_low}
                  y2={bl.heart_rate_baseline_high}
                  fill="#22c55e"
                  fillOpacity={0.1}
                />
              )}
              <Line type="monotone" dataKey="hr" stroke="#2563eb" dot={false} strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <div>
          <p style={{ fontSize: 13, color: '#64748b', marginBottom: 8 }}>呼吸率 (次/分)</p>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="time" tick={{ fontSize: 11 }} />
              <YAxis domain={['auto', 'auto']} tick={{ fontSize: 11 }} />
              <Tooltip />
              {bl?.breathing_rate_baseline_low != null && bl?.breathing_rate_baseline_high != null && (
                <ReferenceArea
                  y1={bl.breathing_rate_baseline_low}
                  y2={bl.breathing_rate_baseline_high}
                  fill="#22c55e"
                  fillOpacity={0.1}
                />
              )}
              <Line type="monotone" dataKey="br" stroke="#16a34a" dot={false} strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
