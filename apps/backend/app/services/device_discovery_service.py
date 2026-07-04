import asyncio
import socket
import time
from dataclasses import dataclass
from typing import Iterable, Union

from app.schemas import DeviceRecord
from app.services.host_network_service import HostNetworkService
from app.services.vendor_lookup_service import VendorLookupService


@dataclass(frozen=True)
class _DiscoveredDevice:
    ip_address: str
    mac_address: str
    hostname: str
    vendor: str
    operating_system: str
    device_type: str
    status: str


class DeviceDiscoveryService:
    def __init__(
        self,
        host_network_service: HostNetworkService,
        vendor_lookup_service: VendorLookupService,
    ) -> None:
        self._host_network_service = host_network_service
        self._vendor_lookup_service = vendor_lookup_service
        self._cache: list[DeviceRecord] = []
        self._last_scan = 0.0
        self._ttl_seconds = 60.0
        self._lock = asyncio.Lock()

    async def scan(self) -> list[DeviceRecord]:
        if self._cache and time.time() - self._last_scan < self._ttl_seconds:
            return self._cache

        async with self._lock:
            if self._cache and time.time() - self._last_scan < self._ttl_seconds:
                return self._cache

            context = self._host_network_service.get_primary_interface()
            devices = await asyncio.to_thread(self._scan_network, context.network_cidr, context.private_ip, context.gateway)
            serialized = [
                DeviceRecord(
                    ip_address=device.ip_address,
                    mac_address=device.mac_address,
                    hostname=device.hostname,
                    vendor=device.vendor,
                    operating_system=device.operating_system,
                    device_type=device.device_type,
                    status=device.status,
                )
                for device in devices
            ]
            self._cache = sorted(serialized, key=lambda item: tuple(self._sort_key(item)))
            self._last_scan = time.time()
            return self._cache

    def _scan_network(self, network_cidr: str, local_ip: str, gateway_ip: str) -> list[_DiscoveredDevice]:
        discovered: dict[str, _DiscoveredDevice] = {}

        try:
            from scapy.all import ARP, Ether, srp  # type: ignore

            packet = Ether(dst="ff:ff:ff:ff:ff:ff") / ARP(pdst=network_cidr)
            answered, _ = srp(packet, timeout=1.5, verbose=0, retry=0)
            for _, response in answered:
                ip_address = str(response.psrc)
                mac_address = str(response.hwsrc)
                discovered[ip_address] = self._build_device(ip_address, mac_address, gateway_ip)
        except Exception:
            pass

        if local_ip != "Unknown" and local_ip not in discovered:
            discovered[local_ip] = self._build_device(local_ip, "Unknown", gateway_ip)

        if gateway_ip != "Unknown" and gateway_ip not in discovered:
            discovered[gateway_ip] = self._build_device(gateway_ip, "Unknown", gateway_ip)

        return list(discovered.values())

    def _build_device(self, ip_address: str, mac_address: str, gateway_ip: str) -> _DiscoveredDevice:
        hostname = self._resolve_hostname(ip_address)
        vendor = self._vendor_lookup_service.lookup(mac_address)
        device_type = self._classify_device(ip_address, hostname, vendor, gateway_ip)

        return _DiscoveredDevice(
            ip_address=ip_address,
            mac_address=mac_address,
            hostname=hostname,
            vendor=vendor,
            operating_system="Unknown",
            device_type=device_type,
            status="online",
        )

    def _resolve_hostname(self, ip_address: str) -> str:
        try:
            hostname, _, _ = socket.gethostbyaddr(ip_address)
            return hostname
        except Exception:
            return "Unknown"

    def _classify_device(self, ip_address: str, hostname: str, vendor: str, gateway_ip: str) -> str:
        value = f"{hostname} {vendor}".lower()
        if ip_address == gateway_ip:
            return "Router"
        if any(token in value for token in ("iphone", "android", "samsung", "xiaomi", "pixel")):
            return "Phone"
        if any(token in value for token in ("printer", "hp", "epson", "brother")):
            return "Printer"
        if any(token in value for token in ("raspberry", "roku", "nest", "echo", "iot", "camera")):
            return "IoT Device"
        if any(token in value for token in ("macbook", "laptop", "notebook")):
            return "Laptop"
        if any(token in value for token in ("desktop", "workstation", "dell", "lenovo", "asus")):
            return "Desktop"
        return "Unknown"

    def _sort_key(self, item: DeviceRecord) -> Iterable[Union[int, str]]:
        priority = {
            "Router": 0,
            "Desktop": 1,
            "Laptop": 2,
            "Phone": 3,
            "Printer": 4,
            "IoT Device": 5,
            "Unknown": 6,
        }
        return [priority.get(item.device_type, 9), item.ip_address]