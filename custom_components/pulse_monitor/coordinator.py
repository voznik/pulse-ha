"""Data coordinator for Pulse."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import PulseClient, PulseError
from .const import DOMAIN, SCAN_INTERVAL_SECONDS
from .helpers import container_key

_LOGGER = logging.getLogger(__name__)

type PulseConfigEntry = ConfigEntry[PulseCoordinator]


class PulseCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    config_entry: PulseConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: PulseConfigEntry, client: PulseClient
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=timedelta(seconds=SCAN_INTERVAL_SECONDS),
        )
        self.client = client

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            summary, agents, containers, alerts = await asyncio.gather(
                self.client.async_get_summary(),
                self.client.async_get_resources("agent"),
                self.client.async_get_resources("app-container"),
                self.client.async_get_alerts(),
            )
        except PulseError as err:
            raise UpdateFailed(str(err)) from err
        return {
            "summary": summary,
            "agents": {r["id"]: r for r in agents},
            "containers": {container_key(r): r for r in containers},
            "alerts": alerts,
        }
