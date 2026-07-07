import axios from 'axios';

const TOKEN_KEY = 'comp9900_token';

export const api = axios.create({
  baseURL: '/api',
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem(TOKEN_KEY);
      if (!window.location.pathname.includes('/login')) {
        window.location.href = '/login';
      }
    }
    return Promise.reject(err);
  }
);

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

export function isLoggedIn(): boolean {
  return !!localStorage.getItem(TOKEN_KEY);
}

export interface ResidentCard {
  id: string;
  name: string;
  bed_status: string;
  activity_status: string | null;
  last_updated: string | null;
  active_alert_count: number;
  highest_alert_severity: string | null;
  risk_level: string;
}

export interface DashboardData {
  resident_id: string;
  resident_name: string;
  bed_status: string;
  bed_status_confidence: number | null;
  activity_status: string | null;
  last_updated: string | null;
  sleep_score: number | null;
  total_sleep_minutes: number | null;
  sleep_efficiency: number | null;
  bed_exit_count: number | null;
  avg_heart_rate: number | null;
  avg_breathing_rate: number | null;
  summary_date: string | null;
  bed_events: Array<{
    timestamp: string;
    bed_status: string;
    activity_status: string;
    confidence: number;
  }>;
  bed_exit_intervals?: Array<{
    start_time: string;
    end_time: string | null;
    duration_minutes: number;
    exceeds_baseline: boolean;
    baseline_minutes: number | null;
  }>;
  vital_samples: Array<{
    timestamp: string;
    heart_rate_bpm: number;
    breathing_rate_per_min: number;
    confidence: number;
  }>;
  baseline: {
    avg_sleep_minutes_7d: number | null;
    avg_sleep_minutes_30d: number | null;
    avg_efficiency_7d: number | null;
    avg_efficiency_30d: number | null;
    avg_bed_exit_count_7d: number | null;
    avg_bed_exit_count_30d: number | null;
    avg_heart_rate_30d: number | null;
    avg_breathing_rate_30d: number | null;
    heart_rate_baseline_low: number | null;
    heart_rate_baseline_high: number | null;
    breathing_rate_baseline_low: number | null;
    breathing_rate_baseline_high: number | null;
  } | null;
  disclaimer: string;
}

export interface PredictionData {
  resident_id: string;
  probability: number;
  risk_level: string;
  windows: Array<{ minutes: number; probability: number; risk_level: string }>;
  explanation: string;
  disclaimer: string;
}

export interface AlertItem {
  id: number;
  resident_id: string;
  resident_name: string;
  alert_type: string;
  severity: string;
  reason: string;
  timestamp: string;
  suggested_action: string;
  acknowledged: boolean;
}

export interface ReportData {
  resident_id: string;
  resident_name: string;
  daily: {
    date: string;
    sleep_score: number;
    total_sleep_minutes: number;
    awake_minutes: number;
    sleep_efficiency: number;
    bed_exit_count: number;
    longest_out_of_bed_minutes: number;
    avg_heart_rate: number;
    avg_breathing_rate: number;
  } | null;
  weekly: Array<{
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
  }>;
  disclaimer: string;
}

export async function login(username: string, password: string) {
  const { data } = await api.post<{ access_token: string }>('/auth/login', { username, password });
  setToken(data.access_token);
}

export async function fetchResidents() {
  const { data } = await api.get<ResidentCard[]>('/residents');
  return data;
}

export async function fetchDashboard(id: string) {
  const { data } = await api.get<DashboardData>(`/residents/${id}/dashboard`);
  return data;
}

export async function fetchPrediction(id: string) {
  const { data } = await api.get<PredictionData>(`/residents/${id}/prediction`);
  return data;
}

export async function fetchAlerts(residentId?: string) {
  const url = residentId ? `/residents/${residentId}/alerts` : '/alerts';
  const { data } = await api.get<{ alerts: AlertItem[]; total: number }>(url);
  return data.alerts;
}

export async function acknowledgeAlert(id: number) {
  await api.post(`/alerts/${id}/acknowledge`);
}

export async function fetchReport(residentId: string, targetDate?: string) {
  const { data } = await api.get<ReportData>(`/reports/${residentId}`, {
    params: targetDate ? { target_date: targetDate } : undefined,
  });
  return data;
}
