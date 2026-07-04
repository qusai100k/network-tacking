import asyncio
import socket
import time
from collections import defaultdict
from typing import Optional

import psutil

from app.schemas import ConnectionRecord
from app.services.geoip_service import GeoIPService

_HIGH_RISK_PORTS = {23, 135, 445, 1337, 3389, 4444, 5555, 6666, 31337}
_COMMON_PORTS = {80, 443, 53, 123, 22, 25, 993, 995, 587}


class ConnectionAnalyzerService:
    def __init__(self, geoip_service: GeoIPService) -> None:
        self._geoip_service = geoip_service
        self._cache: list[ConnectionRecord] = []
        self._last_scan = 0.0
        self._ttl_seconds = 8.0
        self._lock = asyncio.Lock()

    async def scan(self) -> list[ConnectionRecord]:
        if self._cache and time.time() - self._last_scan < self._ttl_seconds:
            return self._cache

        async with self._lock:
            if self._cache and time.time() - self._last_scan < self._ttl_seconds:
                return self._cache

            connections = await asyncio.to_thread(psutil.net_connections, "inet")
            grouped = self._group_connections(connections)

            records: list[ConnectionRecord] = []
            for (remote_ip, remote_port), items in grouped.items():
                application = self._dominant_application(items)
                protocol = self._dominant_protocol(items)
                status = self._dominant_status(items)
                latency_ms = await self._estimate_latency(remote_ip)
                country = await self._geoip_service.country_for_ip(remote_ip)
                score = self._suspicious_score(application, remote_port, country, items)

                records.append(
                    ConnectionRecord(
                        remote_ip=remote_ip,
                        country=country,
                        latency_ms=latency_ms,
                        port=remote_port,
                        protocol=protocol,
                        application=application,
                        status=status,
                        suspicious_score=score,
                    )
                )

            self._cache = sorted(
                records,
                key=lambda item: (-item.suspicious_score, item.application.lower(), item.remote_ip),
            )[:40]
            self._last_scan = time.time()
            return self._cache

    def _group_connections(
        self, connections: list[psutil._common.sconn]
    ) -> dict[tuple[str, int], list[psutil._common.sconn]]:
        grouped: dict[tuple[str, int], list[psutil._common.sconn]] = defaultdict(list)
        for conn in connections:
            if conn.raddr:
                key = (str(conn.raddr.ip), int(conn.raddr.port))
                grouped[key].append(conn)
        return grouped

    def _dominant_application(self, items: list[psutil._common.sconn]) -> str:
        counts: dict[str, int] = defaultdict(int)
        for item in items:
            if not item.pid:
                continue
            process = self._safe_process(item.pid)
            name = process.name() if process else "Unknown"
            counts[name] += 1
        if not counts:
            return "Unknown"
        return max(counts.items(), key=lambda pair: pair[1])[0]

    def _dominant_protocol(self, items: list[psutil._common.sconn]) -> str:
        tcp_count = sum(1 for item in items if item.type == socket.SOCK_STREAM)
        udp_count = sum(1 for item in items if item.type == socket.SOCK_DGRAM)
        if tcp_count and udp_count:
            return "Mixed"
        if tcp_count:
            return "TCP"
        if udp_count:
            return "UDP"
        return "Unknown"

    def _dominant_status(self, items: list[psutil._common.sconn]) -> str:
        counts: dict[str, int] = defaultdict(int)
        for item in items:
            counts[item.status or "NONE"] += 1
        return max(counts.items(), key=lambda pair: pair[1])[0]

    async def _estimate_latency(self, remote_ip: str) -> Optional[float]:
        try:
            from ping3 import ping

            result = await asyncio.to_thread(ping, remote_ip, timeout=1.0, unit="ms")
            if result is None:
                return None
            return round(float(result), 2)
        except Exception:
            return None

    def _suspicious_score(
        self,
        application: str,
        port: int,
        country: str,
        items: list[psutil._common.sconn],
    ) -> int:
        score = 0
        if port in _HIGH_RISK_PORTS:
            score += 40
        elif port not in _COMMON_PORTS and port < 1024:
            score += 15

        if application.lower() in {"unknown", "powershell", "cmd", "python", "nc", "ncat"}:
            score += 20

        if country == "Unknown":
            score += 15

        if len(items) >= 10:
            score += 10

        return min(score, 100)

    def _safe_process(self, pid: int) -> Optional[psutil.Process]:
        try:
            return psutil.Process(pid)
        except Exception:
            return None