import type {
  RawAIAnalysisPayload,
  RawAIChatResponse,
  RawBootstrapPayload,
  RawConnectionRecord,
  RawDeviceRecord,
  RawProcessNetworkRecord
} from "./contracts";

const API_BASE = "http://127.0.0.1:8000";

async function parse<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json"
    },
    ...init
  });

  if (!response.ok) {
    throw new Error(`${path} failed with status ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export async function getBootstrap(): Promise<RawBootstrapPayload> {
  return parse<RawBootstrapPayload>("/api/v1/bootstrap");
}

export async function getDevices(): Promise<RawDeviceRecord[]> {
  return parse<RawDeviceRecord[]>("/api/v1/devices");
}

export async function getProcesses(): Promise<RawProcessNetworkRecord[]> {
  return parse<RawProcessNetworkRecord[]>("/api/v1/processes");
}

export async function getConnections(): Promise<RawConnectionRecord[]> {
  return parse<RawConnectionRecord[]>("/api/v1/connections");
}

export async function getAIAnalysis(): Promise<RawAIAnalysisPayload> {
  return parse<RawAIAnalysisPayload>("/api/v1/ai/analysis");
}

export async function postAIChat(message: string, provider?: string): Promise<RawAIChatResponse> {
  return parse<RawAIChatResponse>("/api/v1/ai/chat", {
    method: "POST",
    body: JSON.stringify({ message, provider })
  });
}

export const wsEndpoint = "ws://127.0.0.1:8000/ws/telemetry";