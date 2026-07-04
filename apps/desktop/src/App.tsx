import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  Bot,
  Cpu,
  HardDrive,
  Network,
  RefreshCw,
  Router,
  Search,
  ShieldAlert,
  Sparkles,
  Wifi
} from "lucide-react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";
import { useAppStore } from "./store/useAppStore";
import type {
  AIAnalysisPayload,
  AIProvider,
  AIRecommendation,
  AlertRecord,
  ChatMessage,
  ConnectionRecord,
  DeviceRecord,
  PredictionRecord,
  ProcessNetworkRecord,
  TelemetrySnapshot
} from "./lib/types";

function formatNumber(value: number, digits = 1) {
  return Number.isFinite(value) ? value.toFixed(digits) : "0.0";
}

function formatOptional(value: number | null | undefined, suffix = "", digits = 1) {
  if (value === null || value === undefined) return "—";
  return `${value.toFixed(digits)}${suffix}`;
}

function formatUptime(seconds: number) {
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  return `${days}d ${hours}h ${minutes}m`;
}

function riskTone(value: string) {
  if (value === "critical") return "text-rose-300 bg-rose-500/15 border-rose-500/20";
  if (value === "high") return "text-orange-300 bg-orange-500/15 border-orange-500/20";
  if (value === "medium") return "text-amber-300 bg-amber-500/15 border-amber-500/20";
  return "text-emerald-300 bg-emerald-500/15 border-emerald-500/20";
}

function MetricCard({
  title,
  value,
  icon,
  tone = "cyan"
}: {
  title: string;
  value: string;
  icon: React.ReactNode;
  tone?: "cyan" | "emerald" | "violet" | "amber" | "rose";
}) {
  const tones = {
    cyan: "from-cyan-500/20 to-blue-500/10 text-cyan-300",
    emerald: "from-emerald-500/20 to-green-500/10 text-emerald-300",
    violet: "from-violet-500/20 to-fuchsia-500/10 text-violet-300",
    amber: "from-amber-500/20 to-orange-500/10 text-amber-300",
    rose: "from-rose-500/20 to-pink-500/10 text-rose-300"
  } as const;

  return (
    <div className={`glass rounded-2xl bg-gradient-to-br ${tones[tone]} p-5 transition-all duration-300 hover:-translate-y-0.5`}>
      <div className="mb-4 flex items-center justify-between">
        <span className="metric-label">{title}</span>
        <span>{icon}</span>
      </div>
      <div className="metric-value">{value}</div>
    </div>
  );
}

function AlertsPanel({ alerts }: { alerts: AlertRecord[] }) {
  return (
    <div className="glass rounded-2xl p-5">
      <div className="mb-4 flex items-center gap-2 text-lg font-semibold">
        <ShieldAlert className="h-5 w-5 text-rose-400" />
        Alert Center
      </div>
      <div className="space-y-3">
        {alerts.length === 0 ? (
          <div className="rounded-xl border border-white/10 bg-white/5 p-4 text-sm text-slate-400">
            No active alerts.
          </div>
        ) : (
          alerts.slice(0, 8).map((alert) => (
            <div key={`${alert.id}-${alert.createdAt}`} className="rounded-xl border border-white/10 bg-white/5 p-4">
              <div className="mb-1 flex items-center justify-between">
                <span className="font-medium capitalize">{alert.kind.replaceAll("_", " ")}</span>
                <span className={`rounded-full border px-2 py-0.5 text-xs uppercase ${riskTone(alert.severity)}`}>
                  {alert.severity}
                </span>
              </div>
              <div className="text-sm text-slate-300">{alert.message}</div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

function SettingsPanel({
  theme,
  aiProvider,
  setTheme,
  setAIProvider,
  refreshOperations
}: {
  theme: "dark" | "light";
  aiProvider: AIProvider;
  setTheme: (value: "dark" | "light") => void;
  setAIProvider: (value: AIProvider) => void;
  refreshOperations: () => Promise<void>;
}) {
  return (
    <div className="glass rounded-2xl p-5">
      <div className="mb-4 flex items-center gap-2 text-lg font-semibold">
        <Bot className="h-5 w-5 text-violet-400" />
        Runtime Settings
      </div>
      <div className="grid gap-4 md:grid-cols-3">
        <label className="rounded-xl border border-white/10 bg-white/5 p-4">
          <div className="mb-2 text-sm text-slate-400">Theme</div>
          <select
            className="w-full rounded-lg border border-white/10 bg-slate-900/80 p-3 text-sm outline-none"
            value={theme}
            onChange={(e) => setTheme(e.target.value as "dark" | "light")}
          >
            <option value="dark">Dark</option>
            <option value="light">Light</option>
          </select>
        </label>
        <label className="rounded-xl border border-white/10 bg-white/5 p-4">
          <div className="mb-2 text-sm text-slate-400">AI Provider</div>
          <select
            className="w-full rounded-lg border border-white/10 bg-slate-900/80 p-3 text-sm outline-none"
            value={aiProvider}
            onChange={(e) => setAIProvider(e.target.value as AIProvider)}
          >
            <option value="ollama">Ollama</option>
            <option value="openai">OpenAI</option>
            <option value="gemini">Gemini</option>
            <option value="claude">Claude</option>
          </select>
        </label>
        <div className="rounded-xl border border-white/10 bg-white/5 p-4">
          <div className="mb-2 text-sm text-slate-400">Operations</div>
          <button
            className="flex w-full items-center justify-center gap-2 rounded-lg border border-cyan-500/20 bg-cyan-500/10 p-3 text-sm text-cyan-200 transition hover:bg-cyan-500/20"
            onClick={() => void refreshOperations()}
          >
            <RefreshCw className="h-4 w-4" />
            Refresh Analysis
          </button>
        </div>
      </div>
    </div>
  );
}

function DeviceTable({ devices }: { devices: DeviceRecord[] }) {
  return (
    <div className="glass rounded-2xl p-5">
      <div className="mb-4 flex items-center gap-2 text-lg font-semibold">
        <Search className="h-5 w-5 text-cyan-300" />
        Discovered Devices
      </div>
      <div className="overflow-auto">
        <table className="min-w-full text-left text-sm">
          <thead className="text-slate-400">
            <tr>
              <th className="pb-3 pr-4">IP</th>
              <th className="pb-3 pr-4">Hostname</th>
              <th className="pb-3 pr-4">Vendor</th>
              <th className="pb-3 pr-4">Type</th>
              <th className="pb-3 pr-4">Status</th>
            </tr>
          </thead>
          <tbody>
            {devices.map((device) => (
              <tr key={device.ipAddress} className="border-t border-white/5">
                <td className="py-3 pr-4">{device.ipAddress}</td>
                <td className="py-3 pr-4">{device.hostname}</td>
                <td className="py-3 pr-4">{device.vendor}</td>
                <td className="py-3 pr-4">{device.deviceType}</td>
                <td className="py-3 pr-4">
                  <span className="rounded-full border border-emerald-500/20 bg-emerald-500/10 px-2 py-1 text-xs text-emerald-300">
                    {device.status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ProcessTable({ processes }: { processes: ProcessNetworkRecord[] }) {
  return (
    <div className="glass rounded-2xl p-5">
      <div className="mb-4 flex items-center gap-2 text-lg font-semibold">
        <Activity className="h-5 w-5 text-violet-300" />
        Process Network Monitor
      </div>
      <div className="overflow-auto">
        <table className="min-w-full text-left text-sm">
          <thead className="text-slate-400">
            <tr>
              <th className="pb-3 pr-4">Application</th>
              <th className="pb-3 pr-4">PID</th>
              <th className="pb-3 pr-4">Current</th>
              <th className="pb-3 pr-4">Upload</th>
              <th className="pb-3 pr-4">Download</th>
              <th className="pb-3 pr-4">Destination</th>
              <th className="pb-3 pr-4">Risk</th>
            </tr>
          </thead>
          <tbody>
            {processes.map((process) => (
              <tr key={`${process.pid}-${process.destinationIp}`} className="border-t border-white/5">
                <td className="py-3 pr-4">{process.application}</td>
                <td className="py-3 pr-4">{process.pid}</td>
                <td className="py-3 pr-4">{formatOptional(process.currentBandwidthKbps, " kbps", 0)}</td>
                <td className="py-3 pr-4">{formatOptional(process.uploadKbps, " kbps", 0)}</td>
                <td className="py-3 pr-4">{formatOptional(process.downloadKbps, " kbps", 0)}</td>
                <td className="py-3 pr-4">
                  {process.destinationIp} · {process.destinationCountry}
                </td>
                <td className="py-3 pr-4">
                  <span className={`rounded-full border px-2 py-1 text-xs uppercase ${riskTone(process.riskLevel)}`}>
                    {process.riskLevel}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ConnectionTable({ connections }: { connections: ConnectionRecord[] }) {
  return (
    <div className="glass rounded-2xl p-5">
      <div className="mb-4 flex items-center gap-2 text-lg font-semibold">
        <Network className="h-5 w-5 text-amber-300" />
        Active Connections
      </div>
      <div className="overflow-auto">
        <table className="min-w-full text-left text-sm">
          <thead className="text-slate-400">
            <tr>
              <th className="pb-3 pr-4">Application</th>
              <th className="pb-3 pr-4">Remote IP</th>
              <th className="pb-3 pr-4">Country</th>
              <th className="pb-3 pr-4">Port</th>
              <th className="pb-3 pr-4">Protocol</th>
              <th className="pb-3 pr-4">Latency</th>
              <th className="pb-3 pr-4">Score</th>
            </tr>
          </thead>
          <tbody>
            {connections.map((connection) => (
              <tr key={`${connection.application}-${connection.remoteIp}-${connection.port}`} className="border-t border-white/5">
                <td className="py-3 pr-4">{connection.application}</td>
                <td className="py-3 pr-4">{connection.remoteIp}</td>
                <td className="py-3 pr-4">{connection.country}</td>
                <td className="py-3 pr-4">{connection.port}</td>
                <td className="py-3 pr-4">{connection.protocol}</td>
                <td className="py-3 pr-4">{formatOptional(connection.latencyMs, " ms", 0)}</td>
                <td className="py-3 pr-4">
                  <span className={`rounded-full border px-2 py-1 text-xs ${connection.suspiciousScore >= 70 ? riskTone("critical") : connection.suspiciousScore >= 45 ? riskTone("high") : connection.suspiciousScore >= 20 ? riskTone("medium") : riskTone("low")}`}>
                    {connection.suspiciousScore}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function AnalysisPanel({ analysis }: { analysis: AIAnalysisPayload | null }) {
  if (!analysis) {
    return (
      <div className="glass rounded-2xl p-5 text-sm text-slate-400">
        Waiting for the first AI analysis cycle...
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="glass rounded-2xl p-5">
        <div className="mb-4 flex items-center gap-2 text-lg font-semibold">
          <Sparkles className="h-5 w-5 text-cyan-300" />
          AI Recommendations
        </div>
        {analysis.recommendations.length === 0 ? (
          <div className="rounded-xl border border-white/10 bg-white/5 p-4 text-sm text-slate-400">
            No issues require attention right now. Network looks healthy.
          </div>
        ) : (
          <div className="space-y-3">
            {analysis.recommendations.map((rec: AIRecommendation) => (
              <div key={rec.id} className="rounded-xl border border-white/10 bg-white/5 p-4">
                <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                  <span className="font-medium">{rec.problemSummary}</span>
                  <div className="flex items-center gap-2">
                    <span className={`rounded-full border px-2 py-0.5 text-xs uppercase ${riskTone(rec.severity)}`}>
                      {rec.severity}
                    </span>
                    <span className="rounded-full border border-cyan-500/20 bg-cyan-500/10 px-2 py-0.5 text-xs text-cyan-200">
                      {rec.confidenceScore}% confidence
                    </span>
                  </div>
                </div>
                <div className="mb-2 text-sm text-slate-300">{rec.technicalExplanation}</div>
                <div className="mb-2 text-xs text-slate-400">
                  <span className="font-medium text-slate-300">Possible cause:</span> {rec.possibleCause}
                </div>
                <ul className="mb-2 list-disc space-y-1 pl-5 text-sm text-slate-300">
                  {rec.recommendedFixes.map((fix: string, index: number) => (
                    <li key={index}>{fix}</li>
                  ))}
                </ul>
                <div className="text-xs text-emerald-300">{rec.estimatedImprovement}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="glass rounded-2xl p-5">
        <div className="mb-4 flex items-center gap-2 text-lg font-semibold">
          <Activity className="h-5 w-5 text-violet-300" />
          Predictive Analytics
        </div>
        {analysis.predictions.length === 0 ? (
          <div className="rounded-xl border border-white/10 bg-white/5 p-4 text-sm text-slate-400">
            Not enough history collected yet to generate predictions.
          </div>
        ) : (
          <div className="grid gap-3 md:grid-cols-2">
            {analysis.predictions.map((prediction: PredictionRecord) => (
              <div key={prediction.metric} className="rounded-xl border border-white/10 bg-white/5 p-4">
                <div className="mb-1 flex items-center justify-between">
                  <span className="font-medium capitalize">{prediction.metric.replaceAll("_", " ")}</span>
                  <span className="text-xs text-slate-400">{prediction.horizon}</span>
                </div>
                <div className="mb-1 text-xl font-semibold">
                  {prediction.predictedValue.toFixed(1)} {prediction.unit}
                </div>
                <div className="text-xs text-slate-400">{prediction.interpretation}</div>
                <div className="mt-2 text-xs text-cyan-300">{prediction.confidenceScore}% confidence</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function ChatPanel({
  chatMessages,
  chatLoading,
  message,
  setMessage,
  onSend
}: {
  chatMessages: ChatMessage[];
  chatLoading: boolean;
  message: string;
  setMessage: (value: string) => void;
  onSend: () => void;
}) {
  return (
    <div className="glass flex h-full flex-col rounded-2xl p-5">
      <div className="mb-4 flex items-center gap-2 text-lg font-semibold">
        <Bot className="h-5 w-5 text-cyan-300" />
        AI Network Assistant
      </div>
      <div className="mb-4 flex-1 space-y-3 overflow-auto pr-1">
        {chatMessages.map((chat) => (
          <div
            key={chat.id}
            className={`max-w-[85%] rounded-xl border px-4 py-2 text-sm ${
              chat.role === "assistant"
                ? "border-cyan-500/20 bg-cyan-500/10 text-cyan-100"
                : "ml-auto border-white/10 bg-white/10 text-slate-100"
            }`}
          >
            {chat.content}
          </div>
        ))}
        {chatLoading && (
          <div className="max-w-[85%] rounded-xl border border-cyan-500/20 bg-cyan-500/10 px-4 py-2 text-sm text-cyan-100">
            Analyzing telemetry...
          </div>
        )}
      </div>
      <form
        className="flex gap-2"
        onSubmit={(event) => {
          event.preventDefault();
          onSend();
        }}
      >
        <input
          className="flex-1 rounded-lg border border-white/10 bg-slate-900/80 p-3 text-sm outline-none focus:border-cyan-500/40"
          placeholder="Ask about latency, bandwidth, devices, or risks..."
          value={message}
          onChange={(event) => setMessage(event.target.value)}
        />
        <button
          type="submit"
          disabled={chatLoading || !message.trim()}
          className="rounded-lg border border-cyan-500/20 bg-cyan-500/10 px-4 text-sm text-cyan-200 transition hover:bg-cyan-500/20 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Send
        </button>
      </form>
    </div>
  );
}

type TabKey = "overview" | "devices" | "processes" | "connections" | "ai" | "settings";

const TABS: { key: TabKey; label: string }[] = [
  { key: "overview", label: "Overview" },
  { key: "devices", label: "Devices" },
  { key: "processes", label: "Processes" },
  { key: "connections", label: "Connections" },
  { key: "ai", label: "AI Insights" },
  { key: "settings", label: "Settings" }
];

export default function App() {
  const [message, setMessage] = useState("");
  const [activeTab, setActiveTab] = useState<TabKey>("overview");
  const {
    telemetry,
    history,
    alerts,
    devices,
    processes,
    connections,
    analysis,
    chatMessages,
    chatLoading,
    connected,
    error,
    theme,
    aiProvider,
    initialize,
    refreshOperations,
    sendChat,
    setTheme,
    setAIProvider
  } = useAppStore();

  useEffect(() => {
    void initialize();
  }, [initialize]);

  const chartData = useMemo(
    () =>
      history.map((sample) => ({
        time: new Date(sample.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }),
        latency: sample.latencyMs,
        jitter: sample.jitterMs,
        download: sample.downloadSpeedMbps,
        upload: sample.uploadSpeedMbps
      })),
    [history]
  );

  const handleSend = () => {
    const trimmed = message.trim();
    if (!trimmed) return;
    void sendChat(trimmed);
    setMessage("");
  };

  return (
    <div className="min-h-screen px-6 py-6">
      <header className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-2xl font-bold tracking-tight">
            <Router className="h-7 w-7 text-cyan-300" />
            NetVision AI
          </div>
          <div className="mt-1 text-sm text-slate-400">Enterprise network monitoring and AI analysis</div>
        </div>
        <div className="flex items-center gap-3">
          <span
            className={`flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-medium ${
              connected ? "border-emerald-500/20 bg-emerald-500/10 text-emerald-300" : "border-rose-500/20 bg-rose-500/10 text-rose-300"
            }`}
          >
            <Wifi className="h-3.5 w-3.5" />
            {connected ? "Live" : "Reconnecting"}
          </span>
          {telemetry && (
            <span
              className={`rounded-full border px-3 py-1.5 text-xs font-medium uppercase ${
                telemetry.internetStatus === "online"
                  ? "border-emerald-500/20 bg-emerald-500/10 text-emerald-300"
                  : telemetry.internetStatus === "degraded"
                    ? "border-amber-500/20 bg-amber-500/10 text-amber-300"
                    : "border-rose-500/20 bg-rose-500/10 text-rose-300"
              }`}
            >
              {telemetry.internetStatus}
            </span>
          )}
        </div>
      </header>

      {error && (
        <div className="mb-4 rounded-xl border border-rose-500/20 bg-rose-500/10 p-3 text-sm text-rose-200">{error}</div>
      )}

      <nav className="mb-6 flex flex-wrap gap-2">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`rounded-lg border px-4 py-2 text-sm font-medium transition ${
              activeTab === tab.key
                ? "border-cyan-500/30 bg-cyan-500/15 text-cyan-200"
                : "border-white/10 bg-white/5 text-slate-300 hover:bg-white/10"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </nav>

      {activeTab === "overview" && telemetry && (
        <div className="space-y-6">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <MetricCard title="Latency" value={`${formatNumber(telemetry.latencyMs)} ms`} icon={<Activity className="h-5 w-5" />} tone="cyan" />
            <MetricCard title="Packet Loss" value={`${formatNumber(telemetry.packetLossPercent)}%`} icon={<ShieldAlert className="h-5 w-5" />} tone="rose" />
            <MetricCard title="Download" value={`${formatNumber(telemetry.downloadSpeedMbps)} Mbps`} icon={<Network className="h-5 w-5" />} tone="emerald" />
            <MetricCard title="Upload" value={`${formatNumber(telemetry.uploadSpeedMbps)} Mbps`} icon={<Network className="h-5 w-5" />} tone="violet" />
            <MetricCard title="Jitter" value={`${formatNumber(telemetry.jitterMs)} ms`} icon={<Wifi className="h-5 w-5" />} tone="amber" />
            <MetricCard title="Bandwidth Usage" value={`${formatNumber(telemetry.bandwidthUsagePercent)}%`} icon={<Cpu className="h-5 w-5" />} tone="cyan" />
            <MetricCard title="CPU" value={`${formatNumber(telemetry.cpuUsagePercent)}%`} icon={<Cpu className="h-5 w-5" />} tone="violet" />
            <MetricCard title="RAM" value={`${formatNumber(telemetry.ramUsagePercent)}%`} icon={<HardDrive className="h-5 w-5" />} tone="emerald" />
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <div className="glass rounded-2xl p-5">
              <div className="mb-4 text-lg font-semibold">Latency &amp; Jitter</div>
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={chartData}>
                  <CartesianGrid stroke="rgba(148,163,184,0.1)" />
                  <XAxis dataKey="time" stroke="rgba(148,163,184,0.5)" fontSize={11} />
                  <YAxis stroke="rgba(148,163,184,0.5)" fontSize={11} />
                  <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid rgba(255,255,255,0.1)" }} />
                  <Line type="monotone" dataKey="latency" stroke="#22d3ee" strokeWidth={2} dot={false} name="Latency (ms)" />
                  <Line type="monotone" dataKey="jitter" stroke="#f472b6" strokeWidth={2} dot={false} name="Jitter (ms)" />
                </LineChart>
              </ResponsiveContainer>
            </div>
            <div className="glass rounded-2xl p-5">
              <div className="mb-4 text-lg font-semibold">Throughput</div>
              <ResponsiveContainer width="100%" height={220}>
                <AreaChart data={chartData}>
                  <CartesianGrid stroke="rgba(148,163,184,0.1)" />
                  <XAxis dataKey="time" stroke="rgba(148,163,184,0.5)" fontSize={11} />
                  <YAxis stroke="rgba(148,163,184,0.5)" fontSize={11} />
                  <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid rgba(255,255,255,0.1)" }} />
                  <Area type="monotone" dataKey="download" stroke="#34d399" fill="#34d399" fillOpacity={0.15} name="Download (Mbps)" />
                  <Area type="monotone" dataKey="upload" stroke="#a78bfa" fill="#a78bfa" fillOpacity={0.15} name="Upload (Mbps)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <AlertsPanel alerts={alerts} />
            <div className="glass rounded-2xl p-5">
              <div className="mb-4 text-lg font-semibold">Network Identity</div>
              <dl className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <dt className="text-slate-400">Adapter</dt>
                  <dd>{telemetry.networkAdapter}</dd>
                </div>
                <div>
                  <dt className="text-slate-400">Connection Type</dt>
                  <dd>{telemetry.connectionType}</dd>
                </div>
                <div>
                  <dt className="text-slate-400">Private IP</dt>
                  <dd>{telemetry.privateIp}</dd>
                </div>
                <div>
                  <dt className="text-slate-400">Public IP</dt>
                  <dd>{telemetry.publicIp}</dd>
                </div>
                <div>
                  <dt className="text-slate-400">Gateway</dt>
                  <dd>{telemetry.gateway}</dd>
                </div>
                <div>
                  <dt className="text-slate-400">DNS</dt>
                  <dd>{telemetry.dns.join(", ")}</dd>
                </div>
                <div>
                  <dt className="text-slate-400">MAC Address</dt>
                  <dd>{telemetry.macAddress}</dd>
                </div>
                <div>
                  <dt className="text-slate-400">ISP</dt>
                  <dd>{telemetry.isp}</dd>
                </div>
                <div>
                  <dt className="text-slate-400">Uptime</dt>
                  <dd>{formatUptime(telemetry.networkUptimeSeconds)}</dd>
                </div>
              </dl>
            </div>
          </div>
        </div>
      )}

      {activeTab === "overview" && !telemetry && (
        <div className="glass rounded-2xl p-8 text-center text-slate-400">Waiting for the first telemetry sample...</div>
      )}

      {activeTab === "devices" && <DeviceTable devices={devices} />}
      {activeTab === "processes" && <ProcessTable processes={processes} />}
      {activeTab === "connections" && <ConnectionTable connections={connections} />}

      {activeTab === "ai" && (
        <div className="grid gap-4 lg:grid-cols-2">
          <AnalysisPanel analysis={analysis} />
          <div className="lg:row-span-1">
            <ChatPanel
              chatMessages={chatMessages}
              chatLoading={chatLoading}
              message={message}
              setMessage={setMessage}
              onSend={handleSend}
            />
          </div>
        </div>
      )}

      {activeTab === "settings" && (
        <SettingsPanel
          theme={theme}
          aiProvider={aiProvider}
          setTheme={setTheme}
          setAIProvider={setAIProvider}
          refreshOperations={refreshOperations}
        />
      )}
    </div>
  );
}