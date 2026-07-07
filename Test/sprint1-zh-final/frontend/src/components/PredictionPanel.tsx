import { PredictionData } from '../api/client';
import { riskColor } from '../utils/format';

interface Props {
  data: PredictionData;
}

export default function PredictionPanel({ data }: Props) {
  return (
    <div className="card">
      <h3 style={{ marginBottom: 12 }}>离床风险预测</h3>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {data.windows.map((w) => (
          <div key={w.minutes} style={{
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            padding: '8px 12px', background: '#f8fafc', borderRadius: 8,
          }}>
            <span>未来 {w.minutes} 分钟</span>
            <span>{(w.probability * 100).toFixed(0)}%</span>
            <span className="badge" style={{ background: riskColor(w.risk_level) }}>
              {w.risk_level}
            </span>
          </div>
        ))}
      </div>
      <p style={{ marginTop: 16, fontSize: 14, color: '#475569', lineHeight: 1.6 }}>
        <strong>原因说明：</strong>{data.explanation}
      </p>
    </div>
  );
}
