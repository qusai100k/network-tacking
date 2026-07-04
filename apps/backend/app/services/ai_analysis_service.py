from datetime import datetime, timezone
from typing import Optional

from app.schemas import (
    AIAnalysisPayload,
    AIRecommendation,
    ConnectionRecord,
    DeviceRecord,
    ProcessNetworkRecord,
    TelemetrySnapshot,
)
from app.services.predictive_analytics_service import PredictiveAnalyticsService


class AIAnalysisService:
    """Produces grounded recommendations and predictions from real telemetry.

    Every recommendation references concrete supporting metrics taken from the
    current snapshot, device list, process list, or connection list. No
    recommendation is emitted unless the underlying condition is actually
    observed in the data.
    """

    def __init__(self, predictive_analytics_service: PredictiveAnalyticsService) -> None:
        self._predictive_analytics_service = predictive_analytics_service

    async def analyze(
        self,
        *,
        telemetry: Optional[TelemetrySnapshot],
        history: list[TelemetrySnapshot],
        devices: list[DeviceRecord],
        processes: list[ProcessNetworkRecord],
        connections: list[ConnectionRecord],
    ) -> AIAnalysisPayload:
        recommendations: list[AIRecommendation] = []

        if telemetry is not None:
            recommendations.extend(self._telemetry_recommendations(telemetry))
            recommendations.extend(self._process_recommendations(processes))
            recommendations.extend(self._connection_recommendations(connections))
            recommendations.extend(self._device_recommendations(devices))

        predictions = self._predictive_analytics_service.predict(history)

        return AIAnalysisPayload(
            generated_at=datetime.now(timezone.utc),
            recommendations=recommendations,
            predictions=predictions,
        )

    def _telemetry_recommendations(self, snapshot: TelemetrySnapshot) -> list[AIRecommendation]:
        recommendations: list[AIRecommendation] = []

        if snapshot.packet_loss_percent >= 5:
            severity = "critical" if snapshot.packet_loss_percent >= 15 else "high"
            recommendations.append(
                AIRecommendation(
                    id="packet-loss",
                    problem_summary=f"Packet loss of {snapshot.packet_loss_percent:.1f}% detected on {snapshot.network_adapter}.",
                    severity=severity,
                    confidence_score=92,
                    possible_cause="Wireless interference, an overloaded router, or an unstable upstream link.",
                    technical_explanation=(
                        f"Recent ICMP probes show {snapshot.packet_loss_percent:.1f}% packet loss with an average "
                        f"latency of {snapshot.latency_ms:.1f} ms over the {snapshot.connection_type} interface."
                    ),
                    recommended_fixes=[
                        "Move closer to the access point or switch to a wired connection.",
                        "Restart the router/modem to clear transient congestion.",
                        "Check for firmware updates on the network adapter and router.",
                    ],
                    estimated_improvement="Packet loss could drop below 1% after resolving the link issue.",
                    priority_level="urgent" if severity == "critical" else "high",
                    supporting_metrics={
                        "packet_loss_percent": snapshot.packet_loss_percent,
                        "latency_ms": snapshot.latency_ms,
                        "network_adapter": snapshot.network_adapter,
                    },
                )
            )

        if snapshot.jitter_ms >= 30:
            recommendations.append(
                AIRecommendation(
                    id="jitter-instability",
                    problem_summary=f"Latency jitter is unstable at {snapshot.jitter_ms:.1f} ms.",
                    severity="medium",
                    confidence_score=85,
                    possible_cause="Bufferbloat, competing bandwidth-heavy applications, or Wi-Fi congestion.",
                    technical_explanation=(
                        f"Consecutive latency samples vary by an average of {snapshot.jitter_ms:.1f} ms, which "
                        "degrades real-time traffic such as voice and video calls."
                    ),
                    recommended_fixes=[
                        "Enable Quality of Service (QoS) on the router for real-time traffic.",
                        "Pause large downloads or cloud backups while on calls.",
                        "Switch to a 5 GHz or wired connection to reduce contention.",
                    ],
                    estimated_improvement="Jitter typically falls below 10 ms once contention is reduced.",
                    priority_level="medium",
                    supporting_metrics={"jitter_ms": snapshot.jitter_ms},
                )
            )

        if snapshot.bandwidth_usage_percent >= 85:
            recommendations.append(
                AIRecommendation(
                    id="bandwidth-saturation",
                    problem_summary=f"Bandwidth utilization is at {snapshot.bandwidth_usage_percent:.1f}% of link capacity.",
                    severity="medium",
                    confidence_score=88,
                    possible_cause="Heavy concurrent downloads, streaming, or background sync processes.",
                    technical_explanation=(
                        f"Throughput is currently {snapshot.throughput_mbps:.1f} Mbps against an interface that "
                        f"is nearly saturated at {snapshot.bandwidth_usage_percent:.1f}% utilization."
                    ),
                    recommended_fixes=[
                        "Identify and pause the highest-bandwidth process in the Process Monitor tab.",
                        "Schedule large downloads or backups for off-peak hours.",
                        "Consider upgrading the internet plan if saturation is frequent.",
                    ],
                    estimated_improvement="Freeing bandwidth-heavy processes can restore headroom immediately.",
                    priority_level="medium",
                    supporting_metrics={
                        "bandwidth_usage_percent": snapshot.bandwidth_usage_percent,
                        "throughput_mbps": snapshot.throughput_mbps,
                    },
                )
            )

        if snapshot.cpu_usage_percent >= 90:
            recommendations.append(
                AIRecommendation(
                    id="high-cpu",
                    problem_summary=f"CPU utilization is high at {snapshot.cpu_usage_percent:.1f}%.",
                    severity="medium",
                    confidence_score=80,
                    possible_cause="A runaway process or background task consuming CPU cycles.",
                    technical_explanation=(
                        f"System CPU load is at {snapshot.cpu_usage_percent:.1f}%, which can delay packet "
                        "processing and increase perceived network latency."
                    ),
                    recommended_fixes=[
                        "Check the Process Monitor tab for unusually active applications.",
                        "Close unused background applications.",
                    ],
                    estimated_improvement="Network responsiveness typically improves once CPU load normalizes.",
                    priority_level="low",
                    supporting_metrics={"cpu_usage_percent": snapshot.cpu_usage_percent},
                )
            )

        if snapshot.internet_status == "offline":
            recommendations.append(
                AIRecommendation(
                    id="connectivity-down",
                    problem_summary="Internet connectivity is currently unavailable.",
                    severity="critical",
                    confidence_score=95,
                    possible_cause="ISP outage, modem/router failure, or a disconnected cable.",
                    technical_explanation="All recent latency probes failed, indicating no route to the internet.",
                    recommended_fixes=[
                        "Check physical cabling and power on the modem and router.",
                        "Restart the modem and router.",
                        "Contact the ISP if the outage persists.",
                    ],
                    estimated_improvement="Restores full connectivity once the underlying cause is resolved.",
                    priority_level="urgent",
                    supporting_metrics={"internet_status": snapshot.internet_status},
                )
            )

        return recommendations

    def _process_recommendations(self, processes: list[ProcessNetworkRecord]) -> list[AIRecommendation]:
        recommendations: list[AIRecommendation] = []
        heavy = [p for p in processes if (p.current_bandwidth_kbps or 0) >= 5000]
        if heavy:
            top = heavy[0]
            recommendations.append(
                AIRecommendation(
                    id=f"heavy-process-{top.pid}",
                    problem_summary=f"{top.application} (PID {top.pid}) is consuming {top.current_bandwidth_kbps:.0f} kbps.",
                    severity="medium",
                    confidence_score=83,
                    possible_cause="A large transfer, sync, or streaming session in this process.",
                    technical_explanation=(
                        f"{top.application} is exchanging data with {top.destination_ip} "
                        f"({top.destination_country}) over {top.protocol} at {top.current_bandwidth_kbps:.0f} kbps."
                    ),
                    recommended_fixes=[
                        f"Pause or close {top.application} if the bandwidth use is unexpected.",
                        "Throttle the application's bandwidth if it supports rate limiting.",
                    ],
                    estimated_improvement="Reduces contention for other applications sharing the link.",
                    priority_level="medium",
                    supporting_metrics={
                        "application": top.application,
                        "current_bandwidth_kbps": top.current_bandwidth_kbps or 0.0,
                        "destination_ip": top.destination_ip,
                    },
                )
            )

        critical_processes = [p for p in processes if p.risk_level == "critical"]
        if critical_processes:
            top = critical_processes[0]
            recommendations.append(
                AIRecommendation(
                    id=f"critical-process-{top.pid}",
                    problem_summary=f"{top.application} (PID {top.pid}) shows critical-risk network behavior.",
                    severity="critical",
                    confidence_score=70,
                    possible_cause="Communication with an unusual destination or suspicious port usage.",
                    technical_explanation=(
                        f"{top.application} is connected to {top.destination_ip} ({top.destination_country}) "
                        f"over {top.protocol} and was flagged as critical risk."
                    ),
                    recommended_fixes=[
                        "Verify this process is expected; terminate it if unrecognized.",
                        "Run an antivirus/anti-malware scan if the process cannot be identified.",
                    ],
                    estimated_improvement="Eliminates a potential security exposure if confirmed malicious.",
                    priority_level="urgent",
                    supporting_metrics={
                        "application": top.application,
                        "destination_ip": top.destination_ip,
                        "risk_level": top.risk_level,
                    },
                )
            )

        return recommendations

    def _connection_recommendations(self, connections: list[ConnectionRecord]) -> list[AIRecommendation]:
        suspicious = [c for c in connections if c.suspicious_score >= 70]
        if not suspicious:
            return []

        top = suspicious[0]
        return [
            AIRecommendation(
                id=f"suspicious-connection-{top.remote_ip}-{top.port}",
                problem_summary=f"High-risk connection to {top.remote_ip}:{top.port} from {top.application}.",
                severity="critical",
                confidence_score=75,
                possible_cause="Connection to an uncommon port or unidentified geographic origin.",
                technical_explanation=(
                    f"{top.application} has an active {top.protocol} connection to {top.remote_ip}:{top.port} "
                    f"({top.country}) with a suspicious score of {top.suspicious_score}/100."
                ),
                recommended_fixes=[
                    "Confirm the destination is expected for this application.",
                    "Block the remote IP at the firewall if it cannot be verified.",
                ],
                estimated_improvement="Closes a potential exfiltration or intrusion vector if confirmed malicious.",
                priority_level="urgent",
                supporting_metrics={
                    "remote_ip": top.remote_ip,
                    "port": top.port,
                    "suspicious_score": top.suspicious_score,
                },
            )
        ]

    def _device_recommendations(self, devices: list[DeviceRecord]) -> list[AIRecommendation]:
        unknown_devices = [d for d in devices if d.vendor == "Unknown" and d.device_type == "Unknown"]
        if len(unknown_devices) < 2:
            return []

        return [
            AIRecommendation(
                id="unidentified-devices",
                problem_summary=f"{len(unknown_devices)} devices on the network could not be identified.",
                severity="low",
                confidence_score=60,
                possible_cause="Devices with randomized MAC addresses or vendors outside the local lookup table.",
                technical_explanation=(
                    f"{len(unknown_devices)} of {len(devices)} discovered devices have no resolvable vendor "
                    "or device type."
                ),
                recommended_fixes=[
                    "Review the device list and confirm each IP belongs to a known device.",
                    "Enable MAC address reservation on the router for easier identification.",
                ],
                estimated_improvement="Improves visibility into all devices connected to the network.",
                priority_level="low",
                supporting_metrics={"unidentified_count": len(unknown_devices), "total_devices": len(devices)},
            )
        ]