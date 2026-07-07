import { DashboardData } from '../api/client';

interface Props {
  data: DashboardData;
}

function formatClock(iso: string) {
  return new Date(iso).toLocaleTimeString('en-AU', { hour: '2-digit', minute: '2-digit' });
}

function timelineBounds(intervals: NonNullable<DashboardData['bed_exit_intervals']>) {
  const starts = intervals.map((iv) => new Date(iv.start_time).getTime());
  const ends = intervals.map((iv) => new Date(iv.end_time ?? new Date().toISOString()).getTime());
  const start = Math.min(...starts);
  const end = Math.max(...ends, start + 60 * 60 * 1000);
  return { start, end };
}

function timeToPercent(iso: string, start: number, end: number): number {
  const value = new Date(iso).getTime();
  return Math.min(100, Math.max(0, ((value - start) / (end - start)) * 100));
}

export default function BedExitTimeline({ data }: Props) {
  const intervals = data.bed_exit_intervals ?? [];
  const bounds = intervals.length > 0 ? timelineBounds(intervals) : null;

  return (
    <div className="card">
      <h3 style={{ marginBottom: 12 }}>Bed-Exit Timeline</h3>
      {intervals.length === 0 || !bounds ? (
        <p style={{ color: '#64748b' }}>No bed-exit intervals recorded</p>
      ) : (
        <>
          <div className="timeline-axis">
            <span>{formatClock(new Date(bounds.start).toISOString())}</span>
            <div className="timeline-track">
              {intervals.map((iv, i) => {
                const left = timeToPercent(iv.start_time, bounds.start, bounds.end);
                const endIso = iv.end_time ?? new Date().toISOString();
                const width = Math.max(timeToPercent(endIso, bounds.start, bounds.end) - left, 3);
                return (
                  <div
                    key={i}
                    className={`timeline-segment ${iv.exceeds_baseline ? 'timeline-segment-warn' : ''}`}
                    style={{ left: `${left}%`, width: `${width}%` }}
                    title={`${formatClock(iv.start_time)} to ${iv.end_time ? formatClock(iv.end_time) : 'ongoing'}`}
                  />
                );
              })}
            </div>
            <span>{formatClock(new Date(bounds.end).toISOString())}</span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 16 }}>
            {intervals.map((iv, i) => (
              <div
                key={i}
                style={{
                  padding: '8px 12px',
                  background: iv.exceeds_baseline ? '#fee2e2' : '#fef3c7',
                  borderRadius: 8,
                  borderLeft: `4px solid ${iv.exceeds_baseline ? '#ef4444' : '#eab308'}`,
                }}
              >
                <strong>
                  Out {formatClock(iv.start_time)}
                  {iv.end_time ? ` to ${formatClock(iv.end_time)}` : ' to ongoing'}
                </strong>
                <span style={{ marginLeft: 12, fontSize: 13, color: '#64748b' }}>
                  {iv.duration_minutes} min
                  {iv.exceeds_baseline && ' | exceeds baseline'}
                </span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
