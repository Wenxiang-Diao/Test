import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';

interface WeeklyPoint {
  date: string;
  total_sleep_minutes: number;
  sleep_efficiency: number;
  bed_exit_count: number;
  avg_heart_rate: number;
  avg_breathing_rate: number;
  baseline_sleep_minutes: number | null;
  baseline_efficiency: number | null;
  baseline_bed_exit_count: number | null;
  baseline_heart_rate: number | null;
  baseline_breathing_rate: number | null;
}

interface ChartSpec {
  title: string;
  dataKey: keyof WeeklyPoint;
  baselineKey: keyof WeeklyPoint;
  unit: string;
  scale?: (v: number) => number;
}

interface Props {
  weekly: WeeklyPoint[];
}

const charts: ChartSpec[] = [
  { title: '睡眠时长', dataKey: 'total_sleep_minutes', baselineKey: 'baseline_sleep_minutes', unit: '分钟' },
  {
    title: '睡眠效率',
    dataKey: 'sleep_efficiency',
    baselineKey: 'baseline_efficiency',
    unit: '%',
    scale: (v) => v * 100,
  },
  { title: '离床次数', dataKey: 'bed_exit_count', baselineKey: 'baseline_bed_exit_count', unit: '次' },
  { title: '平均心率', dataKey: 'avg_heart_rate', baselineKey: 'baseline_heart_rate', unit: 'bpm' },
  { title: '平均呼吸率', dataKey: 'avg_breathing_rate', baselineKey: 'baseline_breathing_rate', unit: '次/分' },
];

function buildChartData(weekly: WeeklyPoint[], spec: ChartSpec) {
  const scale = spec.scale ?? ((v: number) => v);
  return weekly.map((w) => ({
    date: w.date.slice(5),
    value: scale(w[spec.dataKey] as number),
    baseline: w[spec.baselineKey] != null ? scale(w[spec.baselineKey] as number) : null,
  }));
}

export default function WeeklyTrendCharts({ weekly }: Props) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
      {charts.map((spec) => (
        <div key={spec.title}>
          <p style={{ fontSize: 13, color: '#64748b', marginBottom: 8 }}>{spec.title}（{spec.unit}）</p>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={buildChartData(weekly, spec)}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Line type="monotone" dataKey="value" stroke="#2563eb" strokeWidth={2} name="实际" dot />
              <Line
                type="monotone"
                dataKey="baseline"
                stroke="#94a3b8"
                strokeDasharray="5 5"
                name="30天基线"
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      ))}
    </div>
  );
}
