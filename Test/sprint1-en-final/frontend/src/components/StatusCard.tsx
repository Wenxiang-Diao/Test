import { DashboardData } from '../api/client';
import {
  bedStatusColor,
  bedStatusLabel,
  confidenceQualityLabel,
  formatConfidenceLabel,
  formatTime,
  isLowConfidence,
} from '../utils/format';

interface Props {
  data: DashboardData;
}

export default function StatusCard({ data }: Props) {
  const confidence = data.bed_status_confidence;

  return (
    <div className="card" style={{
      background: bedStatusColor(data.bed_status),
      color: 'white',
    }}>
      <div style={{ fontSize: 28, fontWeight: 700 }}>{bedStatusLabel(data.bed_status)}</div>
      <div style={{ marginTop: 8, opacity: 0.9 }}>
        Activity: {data.activity_status || '-'}
      </div>
      <div style={{ marginTop: 4, opacity: 0.85, fontSize: 14 }}>
        Last updated: {formatTime(data.last_updated)}
      </div>
      <div style={{ marginTop: 12, opacity: 0.9 }}>
        Monitoring: {data.monitoring_status}
      </div>
      <div style={{ marginTop: 4, opacity: 0.85, fontSize: 14 }}>
        Location: {data.building || '-'} {data.floor_level ? `Floor ${data.floor_level}` : ''} {data.room_number ? `Room ${data.room_number}` : ''}
      </div>
      <div style={{ marginTop: 12, opacity: 0.9 }}>
        Data quality: {confidenceQualityLabel(confidence)}
      </div>
      <div style={{ marginTop: 4, opacity: 0.85, fontSize: 14 }}>
        Device confidence: {formatConfidenceLabel(confidence)}
      </div>
      {isLowConfidence(confidence) && (
        <div style={{ marginTop: 10, opacity: 0.95, fontSize: 14 }}>
          Note: bed status may be unreliable — please verify on site.
        </div>
      )}
    </div>
  );
}
