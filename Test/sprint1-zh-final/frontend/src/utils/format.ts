export function bedStatusLabel(status: string): string {
  const map: Record<string, string> = {
    IN_BED: '在床',
    OUT_OF_BED: '离床',
    NO_PERSON: '未检测到',
  };
  return map[status] || status;
}

export function bedStatusColor(status: string): string {
  const map: Record<string, string> = {
    IN_BED: '#22c55e',
    OUT_OF_BED: '#eab308',
    NO_PERSON: '#94a3b8',
  };
  return map[status] || '#64748b';
}

export function riskColor(level: string): string {
  if (level === '高') return '#ef4444';
  if (level === '中') return '#f97316';
  return '#22c55e';
}

export function severityColor(severity: string): string {
  return riskColor(severity);
}

export function formatTime(iso: string | null): string {
  if (!iso) return '-';
  return new Date(iso).toLocaleString('zh-CN', {
    month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit',
  });
}

const LOW_CONFIDENCE_THRESHOLD = 0.5;

export function formatConfidenceLabel(confidence: number | null | undefined): string {
  if (confidence === null || confidence === undefined) return '-';
  return `${Math.round(confidence * 100)}%`;
}

export function confidenceQualityLabel(confidence: number | null | undefined): string {
  if (confidence === null || confidence === undefined) return '暂无数据';
  return confidence < LOW_CONFIDENCE_THRESHOLD ? '需确认' : '良好';
}

export function isLowConfidence(confidence: number | null | undefined): boolean {
  return confidence !== null && confidence !== undefined && confidence < LOW_CONFIDENCE_THRESHOLD;
}
