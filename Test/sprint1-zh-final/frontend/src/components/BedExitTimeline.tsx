import { DashboardData } from '../api/client';
import { formatTime } from '../utils/format';

interface Props {
  data: DashboardData;
}

function formatClock(iso: string) {
  return new Date(iso).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
}

/** 将时间映射到 22:00–06:00 睡眠窗口的百分比位置 */
function timeToPercent(iso: string): number {
  const d = new Date(iso);
  const h = d.getHours();
  const m = d.getMinutes();
  let minutesFrom22: number;
  if (h >= 22) {
    minutesFrom22 = (h - 22) * 60 + m;
  } else if (h < 6) {
    minutesFrom22 = (24 - 22) * 60 + h * 60 + m;
  } else {
    minutesFrom22 = 0;
  }
  const windowMinutes = 8 * 60;
  return Math.min(100, Math.max(0, (minutesFrom22 / windowMinutes) * 100));
}

export default function BedExitTimeline({ data }: Props) {
  const intervals = data.bed_exit_intervals ?? [];

  return (
    <div className="card">
      <h3 style={{ marginBottom: 12 }}>今晚离床时间线</h3>
      {intervals.length === 0 ? (
        <p style={{ color: '#64748b' }}>暂无离床区间记录</p>
      ) : (
        <>
          <div className="timeline-axis">
            <span>22:00</span>
            <div className="timeline-track">
              {intervals.map((iv, i) => {
                const left = timeToPercent(iv.start_time);
                const endIso = iv.end_time ?? new Date().toISOString();
                const width = Math.max(timeToPercent(endIso) - left, 3);
                return (
                  <div
                    key={i}
                    className={`timeline-segment ${iv.exceeds_baseline ? 'timeline-segment-warn' : ''}`}
                    style={{ left: `${left}%`, width: `${width}%` }}
                    title={`${formatClock(iv.start_time)} – ${iv.end_time ? formatClock(iv.end_time) : '进行中'}`}
                  />
                );
              })}
            </div>
            <span>06:00</span>
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
                  离床 {formatClock(iv.start_time)}
                  {iv.end_time ? ` – ${formatClock(iv.end_time)}` : ' – 进行中'}
                </strong>
                <span style={{ marginLeft: 12, fontSize: 13, color: '#64748b' }}>
                  持续 {iv.duration_minutes} 分钟
                  {iv.exceeds_baseline && ' · 超出基线'}
                </span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
