import { create } from "zustand";
import {
  getAIAnalysis,
  getBootstrap,
  getConnections,
  getDevices,
  getProcesses,
  postAIChat,
  wsEndpoint
} from "../lib/api";
import {
  normalizeAnalysis,
  normalizeBootstrap,
  normalizeConnection,
  normalizeDevice,
  normalizeEnvelope,
  normalizeProcess,
  normalizeChatResponse
} from "../lib/mappers";
import type { RawTelemetryEnvelope } from "../lib/contracts";
import type {
  AIAnalysisPayload,
  AIProvider,
  AlertRecord,
  ChatMessage,
  ConnectionRecord,
  DeviceRecord,
  ProcessNetworkRecord,
  TelemetrySnapshot,
  ThemeMode
} from "../lib/types";

type State = {
  telemetry: TelemetrySnapshot | null;
  history: TelemetrySnapshot[];
  alerts: AlertRecord[];
  devices: DeviceRecord[];
  processes: ProcessNetworkRecord[];
  connections: ConnectionRecord[];
  analysis: AIAnalysisPayload | null;
  chatMessages: ChatMessage[];
  chatLoading: boolean;
  connected: boolean;
  error: string | null;
  theme: ThemeMode;
  aiProvider: AIProvider;
  initialized: boolean;
  initialize: () => Promise<void>;
  refreshOperations: () => Promise<void>;
  sendChat: (message: string) => Promise<void>;
  setTheme: (theme: ThemeMode) => void;
  setAIProvider: (provider: AIProvider) => void;
};

const HISTORY_LIMIT = 60;
let socket: WebSocket | null = null;
let reconnectTimer: number | null = null;
let operationsTimer: number | null = null;
let initializePromise: Promise<void> | null = null;

function capHistory(history: TelemetrySnapshot[]) {
  return history.slice(-HISTORY_LIMIT);
}

function applyTheme(theme: ThemeMode) {
  document.documentElement.classList.toggle("dark", theme === "dark");
  document.documentElement.classList.toggle("light", theme === "light");
  localStorage.setItem("netvision-theme", theme);
}

function connect() {
  if (socket && socket.readyState <= WebSocket.OPEN) return;

  socket = new WebSocket(wsEndpoint);

  socket.onopen = () => {
    useAppStore.setState({ connected: true, error: null });
  };

  socket.onmessage = (event) => {
    const payload = normalizeEnvelope(JSON.parse(event.data) as RawTelemetryEnvelope);
    useAppStore.setState((state) => ({
      telemetry: payload.telemetry,
      history: capHistory([...state.history, payload.telemetry]),
      alerts: payload.alerts.length ? [...payload.alerts, ...state.alerts].slice(0, 25) : state.alerts
    }));
  };

  socket.onclose = () => {
    useAppStore.setState({ connected: false });
    if (reconnectTimer) window.clearTimeout(reconnectTimer);
    reconnectTimer = window.setTimeout(connect, 2000);
  };

  socket.onerror = () => {
    useAppStore.setState({ connected: false, error: "WebSocket disconnected" });
  };
}

const savedTheme = (localStorage.getItem("netvision-theme") as ThemeMode | null) ?? "dark";
const savedProvider = (localStorage.getItem("netvision-ai-provider") as AIProvider | null) ?? "ollama";

export const useAppStore = create<State>((set, get) => ({
  telemetry: null,
  history: [],
  alerts: [],
  devices: [],
  processes: [],
  connections: [],
  analysis: null,
  chatMessages: [
    {
      id: "welcome",
      role: "assistant",
      content: "Ask about latency, packet loss, bandwidth usage, top network processes, or network optimization.",
      timestamp: new Date().toISOString()
    }
  ],
  chatLoading: false,
  connected: false,
  error: null,
  theme: savedTheme,
  aiProvider: savedProvider,
  initialized: false,
  initialize: async () => {
    if (get().initialized) return;
    if (initializePromise) return initializePromise;

    initializePromise = (async () => {
      applyTheme(savedTheme);
      const bootstrap = normalizeBootstrap(await getBootstrap());
      set({
        telemetry: bootstrap.latest,
        history: bootstrap.history,
        alerts: bootstrap.alerts,
        initialized: true,
        error: null
      });
      await get().refreshOperations();
      connect();

      if (!operationsTimer) {
        operationsTimer = window.setInterval(() => {
          void get().refreshOperations();
        }, 10000);
      }
    })();

    await initializePromise;
  },
  refreshOperations: async () => {
    try {
      const [devices, processes, connections, analysis] = await Promise.all([
        getDevices(),
        getProcesses(),
        getConnections(),
        getAIAnalysis()
      ]);

      set({
        devices: devices.map(normalizeDevice),
        processes: processes.map(normalizeProcess),
        connections: connections.map(normalizeConnection),
        analysis: normalizeAnalysis(analysis),
        error: null
      });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : "Failed to refresh network operations"
      });
    }
  },
  sendChat: async (message) => {
    const trimmed = message.trim();
    if (!trimmed) return;

    const userMessage: ChatMessage = {
      id: `u-${Date.now()}`,
      role: "user",
      content: trimmed,
      timestamp: new Date().toISOString()
    };

    set((state) => ({
      chatMessages: [...state.chatMessages, userMessage],
      chatLoading: true
    }));

    try {
      const response = normalizeChatResponse(await postAIChat(trimmed, get().aiProvider));
      const assistantMessage: ChatMessage = {
        id: `a-${Date.now()}`,
        role: "assistant",
        content: response.answer,
        timestamp: response.generatedAt
      };

      set((state) => ({
        chatMessages: [...state.chatMessages, assistantMessage],
        chatLoading: false,
        error: null
      }));
    } catch (error) {
      const assistantMessage: ChatMessage = {
        id: `a-${Date.now()}`,
        role: "assistant",
        content: "I could not analyze the latest telemetry right now.",
        timestamp: new Date().toISOString()
      };

      set((state) => ({
        chatMessages: [...state.chatMessages, assistantMessage],
        chatLoading: false,
        error: error instanceof Error ? error.message : "AI chat failed"
      }));
    }
  },
  setTheme: (theme) => {
    applyTheme(theme);
    set({ theme });
  },
  setAIProvider: (provider) => {
    localStorage.setItem("netvision-ai-provider", provider);
    set({ aiProvider: provider });
  }
}));