import asyncio
import socket
import time
from collections import defaultdict
from typing import Optional

import psutil

from app.schemas import ProcessNetworkRecord
from app.services.geoip_service import GeoIPService
from app.services.host_network_service import HostNetworkService


class ProcessMonitorService:
    def __init__(
        self,
        geoip_service: GeoIPService,
        host_network_service: HostNetworkService,
    ) -> None:
        self._geoip_service = geoip_service
        self._host_network_service = host_network_service
        self._cache: list[ProcessNetworkRecord] = []
        self._last_scan = 0.0
        self._ttl_seconds = 8.0
        self._lock = asyncio.Lock()

    async def scan(self) -> list[ProcessNetworkRecord]:
        if self._cache and time.time() - self._last_scan < self._ttl_seconds:
            return self._cache

        async with self._lock:
            if self._cache and time.time() - self._last_scan < self._ttl_seconds:
                return self._cache

            host_ips = self._host_network_service.get_primary_interface().host_ips
            connections = await asyncio.to_thread(psutil.net_connections, "inet")
            bandwidth = await self._sample_bandwidth(connections, host_ips)
            grouped = self._group_connections(connections)
            records: list[ProcessNetworkRecord] = []

            for pid, items in grouped.items():
                process = self._safe_process(pid)
                application = process.name() if process else "Unknown"
                remote_ip = self._top_remote(items)
                protocol = self._dominant_protocol(items)
                country = await self._geoip_service.country_for_ip(remote_ip) if remote_ip != "Unknown" else "Unknown"

                upload_kbps, download_kbps = bandwidth.get(pid, (None, None))
                current_kbps = None
                if upload_kbps is not None and download_kbps is not None:
                    current_kbps = round(upload_kbps + download_kbps, 2)

                records.append(
                    ProcessNetworkRecord(
                        application=application,
                        pid=pid,
                        upload_kbps=upload_kbps,
                        download_kbps=download_kbps,
                        current_bandwidth_kbps=current_kbps,
                        destination_ip=remote_ip,
                        destination_country=country,
                        protocol=protocol,
                        risk_level=self._risk_level(application, items, country),
                    )
                )

            self._cache = sorted(
                records,
                key=lambda item: (
                    item.current_bandwidth_kbps is None,
                    -(item.current_bandwidth_kbps or 0.0),
                    item.application.lower(),
                    item.pid,
                ),
            )[:20]
            self._last_scan = time.time()
            return self._cache

    def _group_connections(self, connections: list[psutil._common.sconn]) -> dict[int, list[psutil._common.sconn]]:
        grouped: dict[int, list[psutil._common.sconn]] = defaultdict(list)
        for conn in connections:
            if conn.pid and conn.raddr:
                grouped[int(conn.pid)].append(conn)
        return grouped

    def _top_remote(self, items: list[psutil._common.sconn]) -> str:
        counts: dict[str, int] = defaultdict(int)
        for item in items:
            if item.raddr:
                counts[str(item.raddr.ip)] += 1
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

    def _risk_level(self, application: str, items: list[psutil._common.sconn], country: str) -> str:
        score = 0
        if application.lower() in {"unknown", "powershell", "cmd", "python"}:
            score += 20
        if any(int(item.raddr.port) in {23, 4444, 5555, 1337} for item in items if item.raddr):
            score += 40
        if len(items) >= 20:
            score += 20
        if country == "Unknown":
            score += 10
        if score >= 70:
            return "critical"
        if score >= 45:
            return "high"
        if score >= 20:
            return "medium"
        return "low"

    def _safe_process(self, pid: int) -> Optional[psutil.Process]:
        try:
            return psutil.Process(pid)
        except Exception:
            return None

    async def _sample_bandwidth(
        self,
        connections: list[psutil._common.sconn],
        host_ips: set[str],
    ) -> dict[int, tuple[Optional[float], Optional[float]]]:
        try:
            return await asyncio.to_thread(self._sniff_bandwidth, connections, host_ips)
        except Exception:
            return {}

    def _sniff_bandwidth(
        self,
        connections: list[psutil._common.sconn],
        host_ips: set[str],
    ) -> dict[int, tuple[Optional[float], Optional[float]]]:
        try:
            from scapy.all import IP, TCP, UDP, sniff  # type: ignore
        except Exception:
            return {}

        outbound_map: dict[tuple[str, int, str, int], int] = {}
        inbound_map: dict[tuple[str, str, int, int], int] = {}
        for conn in connections:
            if not conn.pid or not conn.raddr or not conn.laddr:
                continue

            protocol = "tcp" if conn.type == socket.SOCK_STREAM else "udp"
            local_port = int(conn.laddr.port)
            remote_ip = str(conn.raddr.ip)
            remote_port = int(conn.raddr.port)
            outbound_map[(protocol, local_port, remote_ip, remote_port)] = int(conn.pid)
            inbound_map[(protocol, remote_ip, remote_port, local_port)] = int(conn.pid)

        sent_bytes: dict[int, int] = defaultdict(int)
        recv_bytes: dict[int, int] = defaultdict(int)
        duration_seconds = 1.0

        def on_packet(packet) -> None:
            if IP not in packet:
                return

            layer = None
            protocol = None
            if TCP in packet:
                layer = packet[TCP]
                protocol = "tcp"
            elif UDP in packet:
                layer = packet[UDP]
                protocol = "udp"

            if layer is None or protocol is None:
                return

            src_ip = str(packet[IP].src)
            dst_ip = str(packet[IP].dst)
            src_port = int(layer.sport)
            dst_port = int(layer.dport)
            length = int(len(packet))

            outbound_pid = outbound_map.get((protocol, src_port, dst_ip, dst_port))
            if outbound_pid and src_ip in host_ips:
                sent_bytes[outbound_pid] += length
                return

            inbound_pid = inbound_map.get((protocol, src_ip, src_port, dst_port))
            if inbound_pid and dst_ip in host_ips:
                recv_bytes[inbound_pid] += length

        sniff(
            timeout=duration_seconds,
            store=False,
            prn=on_packet,
            count=800,
            filter="tcp or udp",
        )

        result: dict[int, tuple[Optional[float], Optional[float]]] = {}
        for pid in set(list(sent_bytes.keys()) + list(recv_bytes.keys())):
            upload_kbps = round((sent_bytes.get(pid, 0) * 8) / duration_seconds / 1000, 2)
            download_kbps = round((recv_bytes.get(pid, 0) * 8) / duration_seconds / 1000, 2)
            result[pid] = (upload_kbps, download_kbps)
        return result