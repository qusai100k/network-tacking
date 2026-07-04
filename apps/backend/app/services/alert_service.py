from app.schemas import AlertRecord, TelemetrySnapshot


class AlertEvaluator:
    def evaluate(self, snapshot: TelemetrySnapshot) -> list[tuple[str, str, str]]:
        alerts: list[tuple[str, str, str]] = []

        if snapshot.internet_status == "offline":
            alerts.append(("network_down", "critical", "Internet connectivity appears unavailable."))

        if snapshot.packet_loss_percent >= 5:
            alerts.append(
                (
                    "packet_loss",
                    "high",
                    f"Packet loss reached {snapshot.packet_loss_percent:.1f}%, which can severely impact calls and gaming.",
                )
            )

        if snapshot.ping_ms >= 120:
            alerts.append(
                (
                    "high_ping",
                    "high",
                    f"Latency is elevated at {snapshot.ping_ms:.1f} ms.",
                )
            )

        if snapshot.bandwidth_usage_percent >= 85:
            alerts.append(
                (
                    "bandwidth_overload",
                    "medium",
                    f"Bandwidth utilization is {snapshot.bandwidth_usage_percent:.1f}% of the interface capacity.",
                )
            )

        if snapshot.cpu_usage_percent >= 90:
            alerts.append(
                (
                    "high_cpu",
                    "medium",
                    f"CPU utilization is high at {snapshot.cpu_usage_percent:.1f}%, which may affect network handling.",
                )
            )

        if snapshot.ram_usage_percent >= 90:
            alerts.append(
                (
                    "high_ram",
                    "medium",
                    f"Memory utilization is high at {snapshot.ram_usage_percent:.1f}%.",
                )
            )

        if snapshot.jitter_ms >= 30:
            alerts.append(
                (
                    "jitter_instability",
                    "medium",
                    f"Jitter reached {snapshot.jitter_ms:.1f} ms, indicating unstable latency.",
                )
            )

        return alerts