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
        活动状态：{data.activity_status || '-'}
      </div>
      <div style={{ marginTop: 4, opacity: 0.85, fontSize: 14 }}>
        最后更新：{formatTime(data.last_updated)}
      </div>
      <div style={{ marginTop: 12, opacity: 0.9 }}>
        数据质量：{confidenceQualityLabel(confidence)}
      </div>
      <div style={{ marginTop: 4, opacity: 0.85, fontSize: 14 }}>
        设备数据可信度：{formatConfidenceLabel(confidence)}
      </div>
      {isLowConfidence(confidence) && (
        <div style={{ marginTop: 10, opacity: 0.95, fontSize: 14 }}>
          提示：当前床位状态可能不准确，请结合现场情况确认。
        </div>
      )}
    </div>
  );
}
