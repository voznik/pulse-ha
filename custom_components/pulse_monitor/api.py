"""Minimal async client for the Pulse REST API."""

from __future__ import annotations

from typing import Any

import aiohttp


class PulseError(Exception):
    """Base error."""


class PulseAuthError(PulseError):
    """Token rejected (401/403)."""


class PulseConnectionError(PulseError):
    """Pulse unreachable or returned an unusable response."""


class PulseClient:
    def __init__(self, session: aiohttp.ClientSession, url: str, token: str) -> None:
        self._session = session
        self._url = url.rstrip("/")
        self._headers = {"X-API-Token": token}

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        try:
            async with self._session.get(
                f"{self._url}/api/{path}",
                params=params,
                headers=self._headers,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status in (401, 403):
                    raise PulseAuthError(f"HTTP {resp.status}")
                resp.raise_for_status()
                return await resp.json()
        except PulseError:
            raise
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            raise PulseConnectionError(str(err)) from err

    async def async_get_summary(self) -> dict[str, Any]:
        return await self._get("state/summary")

    async def async_get_resources(self, rtype: str) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        page = 1
        while True:
            body = await self._get(
                "resources", {"type": rtype, "limit": 100, "page": page}
            )
            items.extend(body.get("data") or [])
            if page >= (body.get("meta") or {}).get("totalPages", 1):
                return items
            page += 1

    async def async_get_alerts(self) -> list[dict[str, Any]]:
        return await self._get("alerts/active") or []
