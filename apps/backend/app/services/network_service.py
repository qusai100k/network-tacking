import asyncio
import ipaddress
import socket
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import httpx
import netifaces
import psutil
from ping3 import ping

from app.core.config import settings
from app.schemas import TelemetrySnapshot


@dataclass
class InterfaceContext:
    name: str
    connection_type: str
    private_ip: str
    mac_address: str
    gateway: str
    dns: list[str]
    nominal_speed_mbps: float


class NetworkCollector:
    def __init__(self) -> None:
        self._last_counters: Optional[tuple[float, float, float]] = None
        self._latency_window: deque[float] = deque(maxlen=12)
        self._public_ip: str = "Unknown"
        self._isp: str = "Unknown"
        self._last_external_lookup: float = 0.0

    async def collect(self) -> TelemetrySnapshot:
        context = self._get_primary_interface()
        io_counters = psutil.net_io_counters(pernic=True)
        pernic = io_counters.get(context.name) if io_counters else None
        download_speed_mbps = 0.0
        upload_speed_mbps = 0.0

        now = time.monotonic()
        if pernic:
            if self._last_counters:
                previous_ts, previous_recv, previous_sent = self._last_counters
                elapsed = max(now - previous_ts, 0.001)
                download_speed_mbps = max(((pernic.bytes_recv - previous_recv) * 8) / elapsed / 1_000_000, 0.0)
                upload_speed_mbps = max(((pernic.bytes_sent - previous_sent) * 8) / elapsed / 1_000_000, 0.0)
            self._last_counters = (now, float(pernic.bytes_recv), float(pernic.bytes_sent))

        ping_results = await self._probe_latency()
        successful = [value for value in ping_results if value is not None]
        packet_loss_percent = round(((len(ping_results) - len(successful)) / len(ping_results)) * 100, 2)
        latency_ms = round(sum(successful) / len(successful), 2) if successful else 0.0
        ping_ms = latency_ms
        self._latency_window.append(latency_ms if successful else 0.0)
        jitter_ms = self._compute_jitter()

        cpu_usage_percent = psutil.cpu_percent(interval=None)
        ram_usage_percent = psutil.virtual_memory().percent
        disk_usage_percent = psutil.disk_usage("/").percent
        throughput_mbps = round(download_speed_mbps + upload_speed_mbps, 2)
        bandwidth_usage_percent = 0.0
        if context.nominal_speed_mbps > 0:
            bandwidth_usage_percent = round(min((throughput_mbps / context.nominal_speed_mbps) * 100, 100.0), 2)

        await self._refresh_public_network_identity()
        internet_status = self._derive_status(packet_loss_percent, latency_ms)

        return TelemetrySnapshot(
            timestamp=datetime.now(timezone.utc),
            internet_status=internet_status,
            download_speed_mbps=round(download_speed_mbps, 2),
            upload_speed_mbps=round(upload_speed_mbps, 2),
            bandwidth_usage_percent=bandwidth_usage_percent,
            throughput_mbps=throughput_mbps,
            ping_ms=ping_ms,
            latency_ms=latency_ms,
            jitter_ms=jitter_ms,
            packet_loss_percent=packet_loss_percent,
            cpu_usage_percent=round(cpu_usage_percent, 2),
            ram_usage_percent=round(ram_usage_percent, 2),
            disk_usage_percent=round(disk_usage_percent, 2),
            network_adapter=context.name,
            connection_type=context.connection_type,
            public_ip=self._public_ip,
            private_ip=context.private_ip,
            gateway=context.gateway,
            dns=context.dns,
            mac_address=context.mac_address,
            network_uptime_seconds=round(time.time() - psutil.boot_time(), 2),
            isp=self._isp,
        )

    async def _probe_latency(self) -> list[Optional[float]]:
        async def do_ping() -> Optional[float]:
            result = await asyncio.to_thread(ping, "1.1.1.1", timeout=1.5, unit="ms")
            if result is None:
                return None
            return float(result)

        return await asyncio.gather(do_ping(), do_ping(), do_ping())

    def _compute_jitter(self) -> float:
        values = [value for value in self._latency_window if value > 0]
        if len(values) < 2:
            return 0.0
        deltas = [abs(values[index] - values[index - 1]) for index in range(1, len(values))]
        return round(sum(deltas) / len(deltas), 2)

    async def _refresh_public_network_identity(self) -> None:
        if time.time() - self._last_external_lookup < 300:
            return

        try:
            async with httpx.AsyncClient(timeout=settings.public_ip_timeout_seconds) as client:
                response = await client.get("https://ipwho.is/")
                response.raise_for_status()
                payload = response.json()
                if payload.get("success", True):
                    self._public_ip = str(payload.get("ip", "Unknown"))
                    self._isp = str(payload.get("connection", {}).get("isp", "Unknown"))
                    self._last_external_lookup = time.time()
        except Exception:
            pass

    def _get_primary_interface(self) -> InterfaceContext:
        stats = psutil.net_if_stats()
        addrs = psutil.net_if_addrs()
        gateways = netifaces.gateways()

        active_candidates: list[str] = [
            name for name, stat in stats.items() if stat.isup and name in addrs and not name.lower().startswith("lo")
        ]

        dns_servers = self._system_dns()
        gateway_ip = self._default_gateway(gateways)

        interface = self._match_gateway_interface(active_candidates, addrs, gateway_ip)
        if interface is None:
            preferred = sorted(
                active_candidates,
                key=lambda name: (
                    0 if self._classify_connection(name) == "Ethernet" else 1,
                    0 if self._find_ipv4(addrs.get(name, [])) != "Unknown" else 1,
                    name,
                ),
            )
            interface = preferred[0] if preferred else next(iter(addrs.keys()), "unknown")

        ipv4 = self._find_ipv4(addrs.get(interface, []))
        mac = self._find_mac(addrs.get(interface, []))
        speed = float(getattr(stats.get(interface), "speed", 0) or 0)

        return InterfaceContext(
            name=interface,
            connection_type=self._classify_connection(interface),
            private_ip=ipv4,
            mac_address=mac,
            gateway=gateway_ip,
            dns=dns_servers,
            nominal_speed_mbps=speed,
        )

    def _match_gateway_interface(
        self,
        candidates: list[str],
        addrs: dict[str, list],
        gateway_ip: str,
    ) -> Optional[str]:
        """Identifies which NIC actually owns the default route by checking
        whether the gateway IP falls inside that NIC's own subnet. This is
        necessary because psutil and netifaces can report interface
        identifiers differently (especially on Windows), so interface names
        can't be matched directly across the two libraries; matching by
        subnet membership works regardless of naming scheme.
        """
        if gateway_ip == "Unknown":
            return None

        try:
            gateway_addr = ipaddress.ip_address(gateway_ip)
        except ValueError:
            return None

        ranked: list[tuple[int, str]] = []
        for name in candidates:
            for address in addrs.get(name, []):
                if getattr(address, "family", None) != socket.AF_INET:
                    continue
                ip_text = str(address.address)
                netmask_text = str(getattr(address, "netmask", "") or "")
                if not netmask_text:
                    continue
                try:
                    network = ipaddress.ip_network(f"{ip_text}/{netmask_text}", strict=False)
                except ValueError:
                    continue
                if gateway_addr in network:
                    priority = 0 if self._classify_connection(name) == "Ethernet" else 1
                    ranked.append((priority, name))

        if not ranked:
            return None

        ranked.sort(key=lambda item: item[0])
        return ranked[0][1]

    def _default_gateway(self, gateways: dict) -> str:
        default = gateways.get("default", {})
        gateway = default.get(netifaces.AF_INET)
        if gateway:
            return str(gateway[0])
        return "Unknown"

    def _system_dns(self) -> list[str]:
        values: list[str] = []
        try:
            with open("/etc/resolv.conf", "r", encoding="utf-8") as handle:
                for line in handle:
                    line = line.strip()
                    if line.startswith("nameserver "):
                        values.append(line.split(" ", 1)[1].strip())
        except Exception:
            pass
        if values:
            return values[:3]

        try:
            host = socket.gethostbyname_ex(socket.gethostname())[2]
            values.extend(host)
        except Exception:
            pass
        return values[:3] or ["Unknown"]

    def _find_ipv4(self, addresses: list[psutil._common.snicaddr]) -> str:
        for address in addresses:
            if getattr(address, "family", None) == socket.AF_INET:
                candidate = str(address.address)
                try:
                    parsed = ipaddress.ip_address(candidate)
                    if not parsed.is_loopback:
                        return candidate
                except ValueError:
                    continue
        return "Unknown"

    def _find_mac(self, addresses: list[psutil._common.snicaddr]) -> str:
        for address in addresses:
            family = getattr(address, "family", None)
            if family == psutil.AF_LINK or str(family).endswith("AF_LINK"):
                return str(address.address)
        return "Unknown"

    def _classify_connection(self, interface_name: str) -> str:
        name = interface_name.lower()
        if any(token in name for token in ("wi-fi", "wifi", "wlan", "wireless", "wl")):
            return "WiFi"
        if any(token in name for token in ("eth", "en", "ethernet")):
            return "Ethernet"
        if any(token in name for token in ("tun", "tap", "vpn")):
            return "VPN"
        return "Unknown"

    def _derive_status(self, packet_loss_percent: float, latency_ms: float) -> str:
        if packet_loss_percent >= 100:
            return "offline"
        if packet_loss_percent > 5 or latency_ms > 120:
            return "degraded"
        return "online"