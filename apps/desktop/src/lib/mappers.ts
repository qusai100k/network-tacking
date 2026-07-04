import type {
  RawAIAnalysisPayload,
  RawAIChatResponse,
  RawAIRecommendation,
  RawAlertRecord,
  RawBootstrapPayload,
  RawConnectionRecord,
  RawDeviceRecord,
  RawPredictionRecord,
  RawProcessNetworkRecord,
  RawTelemetryEnvelope,
  RawTelemetrySnapshot
} from "./contracts";
import type {
  AIAnalysisPayload,
  AIChatResponse,
  AIRecommendation,
  AlertRecord,
  BootstrapPayload,
  ConnectionRecord,
  DeviceRecord,
  PredictionRecord,
  ProcessNetworkRecord,
  TelemetrySnapshot
} from "./types";

export function normalizeSnapshot(raw: RawTelemetrySnapshot): TelemetrySnapshot {
  return {
    timestamp: raw.timestamp,
    internetStatus: raw.internet_status,
    downloadSpeedMbps: raw.download_speed_mbps,
    uploadSpeedMbps: raw.upload_speed_mbps,
    bandwidthUsagePercent: raw.bandwidth_usage_percent,
    throughputMbps: raw.throughput_mbps,
    pingMs: raw.ping_ms,
    latencyMs: raw.latency_ms,
    jitterMs: raw.jitter_ms,
    packetLossPercent: raw.packet_loss_percent,
    cpuUsagePercent: raw.cpu_usage_percent,
    ramUsagePercent: raw.ram_usage_percent,
    diskUsagePercent: raw.disk_usage_percent,
    networkAdapter: raw.network_adapter,
    connectionType: raw.connection_type,
    publicIp: raw.public_ip,
    privateIp: raw.private_ip,
    gateway: raw.gateway,
    dns: raw.dns,
    macAddress: raw.mac_address,
    networkUptimeSeconds: raw.network_uptime_seconds,
    isp: raw.isp
  };
}

export function normalizeAlert(raw: RawAlertRecord): AlertRecord {
  return {
    id: raw.id,
    kind: raw.kind,
    severity: raw.severity,
    message: raw.message,
    createdAt: raw.created_at
  };
}

export function normalizeBootstrap(raw: RawBootstrapPayload): BootstrapPayload {
  return {
    latest: raw.latest ? normalizeSnapshot(raw.latest) : null,
    history: raw.history.map(normalizeSnapshot),
    alerts: raw.alerts.map(normalizeAlert)
  };
}

export function normalizeEnvelope(raw: RawTelemetryEnvelope): {
  telemetry: TelemetrySnapshot;
  alerts: AlertRecord[];
} {
  return {
    telemetry: normalizeSnapshot(raw.telemetry),
    alerts: (raw.alerts ?? []).map(normalizeAlert)
  };
}

export function normalizeDevice(raw: RawDeviceRecord): DeviceRecord {
  return {
    ipAddress: raw.ip_address,
    macAddress: raw.mac_address,
    hostname: raw.hostname,
    vendor: raw.vendor,
    operatingSystem: raw.operating_system,
    deviceType: raw.device_type,
    status: raw.status
  };
}

export function normalizeProcess(raw: RawProcessNetworkRecord): ProcessNetworkRecord {
  return {
    application: raw.application,
    pid: raw.pid,
    uploadKbps: raw.upload_kbps,
    downloadKbps: raw.download_kbps,
    currentBandwidthKbps: raw.current_bandwidth_kbps,
    destinationIp: raw.destination_ip,
    destinationCountry: raw.destination_country,
    protocol: raw.protocol,
    riskLevel: raw.risk_level
  };
}

export function normalizeConnection(raw: RawConnectionRecord): ConnectionRecord {
  return {
    remoteIp: raw.remote_ip,
    country: raw.country,
    latencyMs: raw.latency_ms,
    port: raw.port,
    protocol: raw.protocol,
    application: raw.application,
    status: raw.status,
    suspiciousScore: raw.suspicious_score
  };
}

function normalizeRecommendation(raw: RawAIRecommendation): AIRecommendation {
  return {
    id: raw.id,
    problemSummary: raw.problem_summary,
    severity: raw.severity,
    confidenceScore: raw.confidence_score,
    possibleCause: raw.possible_cause,
    technicalExplanation: raw.technical_explanation,
    recommendedFixes: raw.recommended_fixes,
    estimatedImprovement: raw.estimated_improvement,
    priorityLevel: raw.priority_level,
    supportingMetrics: raw.supporting_metrics
  };
}

function normalizePrediction(raw: RawPredictionRecord): PredictionRecord {
  return {
    metric: raw.metric,
    horizon: raw.horizon,
    predictedValue: raw.predicted_value,
    unit: raw.unit,
    confidenceScore: raw.confidence_score,
    interpretation: raw.interpretation
  };
}

export function normalizeAnalysis(raw: RawAIAnalysisPayload): AIAnalysisPayload {
  return {
    generatedAt: raw.generated_at,
    recommendations: raw.recommendations.map(normalizeRecommendation),
    predictions: raw.predictions.map(normalizePrediction)
  };
}

export function normalizeChatResponse(raw: RawAIChatResponse): AIChatResponse {
  return {
    generatedAt: raw.generated_at,
    answer: raw.answer
  };
}