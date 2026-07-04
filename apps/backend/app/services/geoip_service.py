import ipaddress
import time

import httpx

from app.core.config import settings


class GeoIPService:
    def __init__(self) -> None:
        self._cache: dict[str, tuple[float, str]] = {}
        self._ttl_seconds = 86400.0

    async def country_for_ip(self, ip: str) -> str:
        if not ip:
            return "Unknown"

        try:
            parsed = ipaddress.ip_address(ip)
            if parsed.is_private or parsed.is_loopback or parsed.is_link_local:
                return "Local"
        except ValueError:
            return "Unknown"

        cached = self._cache.get(ip)
        if cached and time.time() - cached[0] < self._ttl_seconds:
            return cached[1]

        country = "Unknown"
        try:
            async with httpx.AsyncClient(timeout=settings.public_ip_timeout_seconds) as client:
                response = await client.get(f"https://ipwho.is/{ip}")
                response.raise_for_status()
                payload = response.json()
                if payload.get("success", True):
                    country = str(payload.get("country") or "Unknown")
        except Exception:
            pass

        self._cache[ip] = (time.time(), country)
        return country