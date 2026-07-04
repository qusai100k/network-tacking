export interface RawTelemetrySnapshot {
  timestamp: string;
  internet_status: "online" | "degraded" | "offline";
  download_speed_mbps: number;
  upload_speed_mbps: number;
  bandwidth_usage_percent: number;
  throughput_mbps: number;
  ping_ms: number;
  latency_ms: number;
  jitter_ms: number;
  packet_loss_percent: number;
  cpu_usage_percent: number;
  ram_usage_percent: number;
  disk_usage_percent: number;
  network_adapter: string;
  connection_type: string;
  public_ip: string;
  private_ip: string;
  gateway: string;
  dns: string[];
  mac_address: string;
  network_uptime_seconds: number;
  isp: string;
}

export interface RawAlertRecord {
  id: number;
  kind: string;
  severity: "low" | "medium" | "high" | "critical";
  message: string;
  created_at: string;
}

export interface RawBootstrapPayload {
  latest: RawTelemetrySnapshot | null;
  history: RawTelemetrySnapshot[];
  alerts: RawAlertRecord[];
}

export interface RawTelemetryEnvelope {
  telemetry: RawTelemetrySnapshot;
  alerts?: RawAlertRecord[];
}

export interface RawDeviceRecord {
  ip_address: string;
  mac_address: string;
  hostname: string;
  vendor: string;
  operating_system: string;
  device_type: string;
  status: string;
}

export interface RawProcessNetworkRecord {
  application: string;
  pid: number;
  upload_kbps: number | null;
  download_kbps: number | null;
  current_bandwidth_kbps: number | null;
  destination_ip: string;
  destination_country: string;
  protocol: string;
  risk_level: string;
}

export interface RawConnectionRecord {
  remote_ip: string;
  country: string;
  latency_ms: number | null;
  port: number;
  protocol: string;
  application: string;
  status: string;
  suspicious_score: number;
}

export interface RawAIRecommendation {
  id: string;
  problem_summary: string;
  severity: "low" | "medium" | "high" | "critical";
  confidence_score: number;
  possible_cause: string;
  technical_explanation: string;
  recommended_fixes: string[];
  estimated_improvement: string;
  priority_level: "low" | "medium" | "high" | "urgent";
  supporting_metrics: Record<string, string | number>;
}

export interface RawPredictionRecord {
  metric: string;
  horizon: string;
  predicted_value: number;
  unit: string;
  confidence_score: number;
  interpretation: string;
}

export interface RawAIAnalysisPayload {
  generated_at: string;
  recommendations: RawAIRecommendation[];
  predictions: RawPredictionRecord[];
}

export interface RawAIChatResponse {
  generated_at: string;
  answer: string;
}