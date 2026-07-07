export function bedStatusLabel(status: string): string {
  const map: Record<string, string> = {
    IN_BED: 'In Bed',
    OUT_OF_BED: 'Out of Bed',
    NO_PERSON: 'No Person',
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
  if (level === 'High') return '#ef4444';
  if (level === 'Medium') return '#f97316';
  return '#22c55e';
}

export function severityColor(severity: string): string {
  return riskColor(severity);
}

export function formatTime(iso: string | null): string {
  if (!iso) return '-';
  return new Date(iso).toLocaleString('en-AU', {
    month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit',
  });
}

const LOW_CONFIDENCE_THRESHOLD = 0.5;

export function formatConfidenceLabel(confidence: number | null | undefined): string {
  if (confidence === null || confidence === undefined) return '-';
  return `${Math.round(confidence * 100)}%`;
}

export function confidenceQualityLabel(confidence: number | null | undefined): string {
  if (confidence === null || confidence === undefined) return 'No data';
  return confidence < LOW_CONFIDENCE_THRESHOLD ? 'Needs review' : 'Good';
}

export function isLowConfidence(confidence: number | null | undefined): boolean {
  return confidence !== null && confidence !== undefined && confidence < LOW_CONFIDENCE_THRESHOLD;
}
