"""
GoDaddy DNS API v1 provider.

Credentials are read from process environment at init — never exposed
to tool callers. This module is called by the server process, not by agents.

GoDaddy API docs: https://developer.godaddy.com/doc/endpoint/domains

Phase 1: Contract and interface only. Live API calls gated behind approval queue.
Phase 2: Execute approved mutations via httpx.
"""

import os
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class DNSProvider(ABC):
    """Abstract DNS provider interface. GoDaddy first, extensible later."""

    @abstractmethod
    async def get_records(
        self, domain: str, record_type: Optional[str] = None, name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch DNS records from provider API."""

    @abstractmethod
    async def create_record(
        self, domain: str, name: str, record_type: str, value: str, ttl: int,
    ) -> Dict[str, Any]:
        """Create a DNS record via provider API."""

    @abstractmethod
    async def update_record(
        self, domain: str, name: str, record_type: str, value: str, ttl: int,
    ) -> Dict[str, Any]:
        """Update a DNS record via provider API."""

    @abstractmethod
    async def delete_record(
        self, domain: str, name: str, record_type: str,
    ) -> Dict[str, Any]:
        """Delete a DNS record via provider API."""


class GoDaddyProvider(DNSProvider):
    """GoDaddy DNS API v1 implementation.

    API Authentication: sso-key {api_key}:{api_secret}
    Production: https://api.godaddy.com/v1
    Test (OTE): https://api.ote-godaddy.com/v1
    """

    PRODUCTION_BASE = "https://api.godaddy.com/v1"
    OTE_BASE = "https://api.ote-godaddy.com/v1"

    def __init__(self):
        self.api_key = os.environ.get("GODADDY_API_KEY", "")
        self.api_secret = os.environ.get("GODADDY_API_SECRET", "")
        env = os.getenv("GODADDY_API_ENV", "production").lower()
        self.base_url = self.OTE_BASE if env == "ote" else self.PRODUCTION_BASE
        self._available = bool(self.api_key and self.api_secret)

    @property
    def available(self) -> bool:
        return self._available

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"sso-key {self.api_key}:{self.api_secret}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def get_records(
        self, domain: str, record_type: Optional[str] = None, name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """GET /v1/domains/{domain}/records[/{type}[/{name}]]"""
        url = f"{self.base_url}/domains/{domain}/records"
        if record_type:
            url += f"/{record_type.upper()}"
            if name:
                url += f"/{name}"

        # Phase 2: httpx.AsyncClient().get(url, headers=self._headers())
        return [{"_note": "Phase 2: live API call", "url": url}]

    async def create_record(
        self, domain: str, name: str, record_type: str, value: str, ttl: int,
    ) -> Dict[str, Any]:
        """PATCH /v1/domains/{domain}/records (append)"""
        url = f"{self.base_url}/domains/{domain}/records"
        payload = [{"type": record_type.upper(), "name": name, "data": value, "ttl": ttl}]

        # Phase 2: httpx.AsyncClient().patch(url, json=payload, headers=self._headers())
        return {"_note": "Phase 2: live API call", "url": url, "payload": payload}

    async def update_record(
        self, domain: str, name: str, record_type: str, value: str, ttl: int,
    ) -> Dict[str, Any]:
        """PUT /v1/domains/{domain}/records/{type}/{name}"""
        url = f"{self.base_url}/domains/{domain}/records/{record_type.upper()}/{name}"
        payload = [{"data": value, "ttl": ttl}]

        # Phase 2: httpx.AsyncClient().put(url, json=payload, headers=self._headers())
        return {"_note": "Phase 2: live API call", "url": url, "payload": payload}

    async def delete_record(
        self, domain: str, name: str, record_type: str,
    ) -> Dict[str, Any]:
        """DELETE /v1/domains/{domain}/records/{type}/{name}"""
        url = f"{self.base_url}/domains/{domain}/records/{record_type.upper()}/{name}"

        # Phase 2: httpx.AsyncClient().delete(url, headers=self._headers())
        return {"_note": "Phase 2: live API call", "url": url}
