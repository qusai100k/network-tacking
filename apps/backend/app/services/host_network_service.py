import ipaddress
import socket
from dataclasses import dataclass

import netifaces
import psutil


@dataclass(frozen=True)
class PrimaryInterfaceContext:
    name: str
    connection_type: str
    private_ip: str
    mac_address: str
    gateway: str
    dns: list[str]
    nominal_speed_mbps: float
    network_cidr: str
    host_ips: set[str]


class HostNetworkService:
    def get_primary_interface(self) -> PrimaryInterfaceContext:
        stats = psutil.net_if_stats()
        addrs = psutil.net_if_addrs()
        gateways = netifaces.gateways()

        active_candidates = [
            name for name, stat in stats.items() if stat.isup and name in addrs and not name.lower().startswith("lo")
        ]
        preferred = sorted(
            active_candidates,
            key=lambda name: (
                0 if self._classify_connection(name) == "Ethernet" else 1,
                0 if self._find_ipv4(addrs.get(name, [])) != "Unknown" else 1,
                name,
            ),
        )
        interface = preferred[0] if preferred else next(iter(addrs.keys()), "unknown")
        interface_addresses = addrs.get(interface, [])

        private_ip = self._find_ipv4(interface_addresses)
        netmask = self._find_netmask(interface_addresses)
        network_cidr = self._find_network(private_ip, netmask)

        return PrimaryInterfaceContext(
            name=interface,
            connection_type=self._classify_connection(interface),
            private_ip=private_ip,
            mac_address=self._find_mac(interface_addresses),
            gateway=self._default_gateway(gateways),
            dns=self._system_dns(),
            nominal_speed_mbps=float(getattr(stats.get(interface), "speed", 0) or 0),
            network_cidr=network_cidr,
            host_ips=self._host_ips(addrs),
        )

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

    def _host_ips(self, addrs: dict) -> set[str]:
        values: set[str] = set()
        for interface_addresses in addrs.values():
            for address in interface_addresses:
                if getattr(address, "family", None) == socket.AF_INET:
                    candidate = str(address.address)
                    try:
                        parsed = ipaddress.ip_address(candidate)
                        if not parsed.is_loopback:
                            values.add(candidate)
                    except ValueError:
                        continue
        return values

    def _find_network(self, private_ip: str, netmask: str) -> str:
        if private_ip == "Unknown":
            return "192.168.1.0/24"

        try:
            if netmask != "Unknown":
                network = ipaddress.ip_network(f"{private_ip}/{netmask}", strict=False)
            else:
                network = ipaddress.ip_network(f"{private_ip}/24", strict=False)

            if network.prefixlen < 24:
                network = ipaddress.ip_network(f"{private_ip}/24", strict=False)

            return str(network)
        except ValueError:
            return "192.168.1.0/24"

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

    def _find_netmask(self, addresses: list[psutil._common.snicaddr]) -> str:
        for address in addresses:
            if getattr(address, "family", None) == socket.AF_INET and getattr(address, "netmask", None):
                return str(address.netmask)
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