export type ThemeMode = "dark" | "light";
export type AIProvider = "ollama" | "openai" | "gemini" | "claude";

export interface TelemetrySnapshot {
  timestamp: string;
  internetStatus: "online" | "degraded" | "offline";
  downloadSpeedMbps: number;
  uploadSpeedMbps: number;
  bandwidthUsagePercent: number;
  throughputMbps: number;
  pingMs: number;
  latencyMs: number;
  jitterMs: number;
  packetLossPercent: number;
  cpuUsagePercent: number;
  ramUsagePercent: number;
  diskUsagePercent: number;
  networkAdapter: string;
  connectionType: string;
  publicIp: string;
  privateIp: string;
  gateway: string;
  dns: string[];
  macAddress: string;
  networkUptimeSeconds: number;
  isp: string;
}

export interface AlertRecord {
  id: number;
  kind: string;
  severity: "low" | "medium" | "high" | "critical";
  message: string;
  createdAt: string;
}

export interface BootstrapPayload {
  latest: TelemetrySnapshot | null;
  history: TelemetrySnapshot[];
  alerts: AlertRecord[];
}

export interface DeviceRecord {
  ipAddress: string;
  macAddress: string;
  hostname: string;
  vendor: string;
  operatingSystem: string;
  deviceType: string;
  status: string;
}

export interface ProcessNetworkRecord {
  application: string;
  pid: number;
  uploadKbps: number | null;
  downloadKbps: number | null;
  currentBandwidthKbps: number | null;
  destinationIp: string;
  destinationCountry: string;
  protocol: string;
  riskLevel: string;
}

export interface ConnectionRecord {
  remoteIp: string;
  country: string;
  latencyMs: number | null;
  port: number;
  protocol: string;
  application: string;
  status: string;
  suspiciousScore: number;
}

export interface AIRecommendation {
  id: string;
  problemSummary: string;
  severity: "low" | "medium" | "high" | "critical";
  confidenceScore: number;
  possibleCause: string;
  technicalExplanation: string;
  recommendedFixes: string[];
  estimatedImprovement: string;
  priorityLevel: "low" | "medium" | "high" | "urgent";
  supportingMetrics: Record<string, string | number>;
}

export interface PredictionRecord {
  metric: string;
  horizon: string;
  predictedValue: number;
  unit: string;
  confidenceScore: number;
  interpretation: string;
}

export interface AIAnalysisPayload {
  generatedAt: string;
  recommendations: AIRecommendation[];
  predictions: PredictionRecord[];
}

export interface AIChatResponse {
  generatedAt: string;
  answer: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
}