import json
from datetime import datetime, timezone
from typing import Optional

from app.schemas import (
    AIAnalysisPayload,
    AIChatResponse,
    ConnectionRecord,
    DeviceRecord,
    ProcessNetworkRecord,
    TelemetrySnapshot,
)
from app.services.ai_provider_client import AIProviderClient, AIProviderError


class AIChatService:
    """Answers natural-language questions grounded in the real, currently
    collected telemetry, device, process, connection, and analysis data.

    If a real LLM provider (OpenAI, Gemini, Claude, or a local Ollama
    instance) is configured and reachable, the question and the live data
    snapshot are sent to it so it can produce a natural-language answer.
    If no provider is configured, or the call fails for any reason (missing
    API key, network error, provider outage), this transparently falls back
    to a deterministic, keyword-grounded engine that composes answers
    directly from the live figures — so the assistant never goes silent and
    never fabricates a metric that wasn't actually observed.
    """

    def __init__(self, provider_client: Optional[AIProviderClient] = None) -> None:
        self._provider_client = provider_client or AIProviderClient()

    async def answer(
        self,
        *,
        message: str,
        telemetry: Optional[TelemetrySnapshot],
        devices: list[DeviceRecord],
        processes: list[ProcessNetworkRecord],
        connections: list[ConnectionRecord],
        analysis: AIAnalysisPayload,
        provider: Optional[str] = None,
    ) -> AIChatResponse:
        if telemetry is None:
            return self._respond("Telemetry hasn't been collected yet. Please wait a moment and try again.")

        if provider:
            try:
                llm_answer = await self._answer_with_provider(
                    provider=provider,
                    message=message,
                    telemetry=telemetry,
                    devices=devices,
                    processes=processes,
                    connections=connections,
                    analysis=analysis,
                )
                return self._respond(llm_answer)
            except AIProviderError as error:
                rule_based_answer = self._answer_with_rules(
                    message, telemetry, devices, processes, connections, analysis
                )
                return self._respond(f"{rule_based_answer}\n\n(Note: {provider} is unavailable — {error})")

        return self._respond(self._answer_with_rules(message, telemetry, devices, processes, connections, analysis))

    async def _answer_with_provider(
        self,
        *,
        provider: str,
        message: str,
        telemetry: TelemetrySnapshot,
        devices: list[DeviceRecord],
        processes: list[ProcessNetworkRecord],
        connections: list[ConnectionRecord],
        analysis: AIAnalysisPayload,
    ) -> str:
        context = {
            "telemetry": json.loads(telemetry.model_dump_json()),
            "device_count": len(devices),
            "top_processes": [
                json.loads(p.model_dump_json())
                for p in sorted(processes, key=lambda p: -(p.current_bandwidth_kbps or 0))[:5]
            ],
            "flagged_connections": [
                json.loads(c.model_dump_json()) for c in connections if c.suspicious_score >= 45
            ][:5],
            "recommendations": [r.problem_summary for r in analysis.recommendations],
            "predictions": [p.interpretation for p in analysis.predictions],
        }

        system_prompt = (
            "You are NetVision AI's network assistant, embedded in a desktop network monitoring app. "
            "Answer the user's question about their network using ONLY the JSON context provided below. "
            "Never invent metrics that aren't in the context. Be concise, specific, and reference actual "
            "numbers from the context. If the context doesn't contain enough information to answer, say so.\n\n"
            f"Live network context:\n{json.dumps(context, default=str)}"
        )

        return await self._provider_client.complete(provider, system_prompt, message)

    def _answer_with_rules(
        self,
        message: str,
        telemetry: TelemetrySnapshot,
        devices: list[DeviceRecord],
        processes: list[ProcessNetworkRecord],
        connections: list[ConnectionRecord],
        analysis: AIAnalysisPayload,
    ) -> str:
        text = message.lower().strip()

        handlers = (
            (("packet loss", "drop", "dropping"), lambda: self._packet_loss(telemetry)),
            (("jitter",), lambda: self._jitter(telemetry)),
            (("latency", "ping", "lag"), lambda: self._latency(telemetry)),
            (("bandwidth", "throughput", "speed"), lambda: self._bandwidth(telemetry)),
            (("cpu",), lambda: self._cpu(telemetry)),
            (("ram", "memory"), lambda: self._ram(telemetry)),
            (("device", "who's connected", "who is connected", "network device"), lambda: self._devices(devices)),
            (("process", "application", "app using", "bandwidth hog"), lambda: self._processes(processes)),
            (("connection", "suspicious", "risk"), lambda: self._connections(connections)),
            (("recommend", "fix", "improve", "advice", "suggestion"), lambda: self._recommendations(analysis)),
            (("predict", "forecast", "future", "trend"), lambda: self._predictions(analysis)),
            (("status", "summary", "overview", "how is", "how's"), lambda: self._summary(telemetry)),
        )

        for keywords, handler in handlers:
            if any(keyword in text for keyword in keywords):
                return handler()

        return self._summary(telemetry)

    def _respond(self, answer: str) -> AIChatResponse:
        return AIChatResponse(generated_at=datetime.now(timezone.utc), answer=answer)

    def _summary(self, telemetry: TelemetrySnapshot) -> str:
        return (
            f"Network is currently {telemetry.internet_status}. Latency is {telemetry.latency_ms:.1f} ms with "
            f"{telemetry.packet_loss_percent:.1f}% packet loss and {telemetry.jitter_ms:.1f} ms of jitter. "
            f"Throughput is {telemetry.throughput_mbps:.1f} Mbps "
            f"({telemetry.download_speed_mbps:.1f} Mbps down / {telemetry.upload_speed_mbps:.1f} Mbps up) "
            f"over {telemetry.connection_type} on {telemetry.network_adapter}."
        )

    def _packet_loss(self, telemetry: TelemetrySnapshot) -> str:
        if telemetry.packet_loss_percent < 1:
            return f"Packet loss is negligible at {telemetry.packet_loss_percent:.1f}%. The connection looks healthy."
        return (
            f"Packet loss is currently {telemetry.packet_loss_percent:.1f}% on {telemetry.network_adapter}. "
            "This can cause stuttering in calls and games; check the Alert Center for related recommendations."
        )

    def _jitter(self, telemetry: TelemetrySnapshot) -> str:
        return (
            f"Jitter is {telemetry.jitter_ms:.1f} ms. "
            + ("That's stable." if telemetry.jitter_ms < 20 else "That's elevated and may affect real-time traffic.")
        )

    def _latency(self, telemetry: TelemetrySnapshot) -> str:
        return (
            f"Current latency is {telemetry.latency_ms:.1f} ms (ping {telemetry.ping_ms:.1f} ms) on "
            f"{telemetry.connection_type}. "
            + ("This is in a healthy range." if telemetry.latency_ms < 60 else "This is higher than ideal for real-time applications.")
        )

    def _bandwidth(self, telemetry: TelemetrySnapshot) -> str:
        return (
            f"Throughput is {telemetry.throughput_mbps:.1f} Mbps total "
            f"({telemetry.download_speed_mbps:.1f} Mbps down / {telemetry.upload_speed_mbps:.1f} Mbps up), "
            f"using {telemetry.bandwidth_usage_percent:.1f}% of the interface's nominal capacity."
        )

    def _cpu(self, telemetry: TelemetrySnapshot) -> str:
        return f"CPU utilization is at {telemetry.cpu_usage_percent:.1f}%."

    def _ram(self, telemetry: TelemetrySnapshot) -> str:
        return f"Memory utilization is at {telemetry.ram_usage_percent:.1f}%."

    def _devices(self, devices: list[DeviceRecord]) -> str:
        if not devices:
            return "No devices have been discovered on the network yet."
        named = ", ".join(f"{d.hostname} ({d.ip_address})" for d in devices[:6])
        more = f", and {len(devices) - 6} more" if len(devices) > 6 else ""
        return f"{len(devices)} devices are currently on the network: {named}{more}."

    def _processes(self, processes: list[ProcessNetworkRecord]) -> str:
        if not processes:
            return "No active outbound process connections were detected."
        ranked = sorted(processes, key=lambda p: -(p.current_bandwidth_kbps or 0))[:3]
        details = ", ".join(
            f"{p.application} ({p.current_bandwidth_kbps or 0:.0f} kbps)" for p in ranked
        )
        return f"Top bandwidth consumers right now: {details}."

    def _connections(self, connections: list[ConnectionRecord]) -> str:
        suspicious = [c for c in connections if c.suspicious_score >= 45]
        if not suspicious:
            return f"All {len(connections)} active connections currently look normal; nothing flagged as risky."
        details = ", ".join(f"{c.application} -> {c.remote_ip}:{c.port} (score {c.suspicious_score})" for c in suspicious[:3])
        return f"{len(suspicious)} connection(s) flagged as elevated risk: {details}."

    def _recommendations(self, analysis: AIAnalysisPayload) -> str:
        if not analysis.recommendations:
            return "No issues require attention right now; the network looks healthy."
        top = sorted(analysis.recommendations, key=lambda r: -r.confidence_score)[:3]
        details = "; ".join(f"{r.problem_summary} (fix: {r.recommended_fixes[0]})" for r in top)
        return f"Top recommendations: {details}."

    def _predictions(self, analysis: AIAnalysisPayload) -> str:
        if not analysis.predictions:
            return "Not enough history has been collected yet to generate reliable predictions."
        details = "; ".join(p.interpretation for p in analysis.predictions[:3])
        return details