"""Pulse monitoring integration."""

from __future__ import annotations

from homeassistant.const import CONF_URL, CONF_VERIFY_SSL, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import DeviceEntry

from .api import PulseClient
from .const import CONF_API_TOKEN, DOMAIN
from .coordinator import PulseConfigEntry, PulseCoordinator
from .helpers import is_stale

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: PulseConfigEntry) -> bool:
    session = async_get_clientsession(hass, entry.data[CONF_VERIFY_SSL])
    client = PulseClient(session, entry.data[CONF_URL], entry.data[CONF_API_TOKEN])
    coordinator = PulseCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_remove_config_entry_device(
    hass: HomeAssistant, entry: PulseConfigEntry, device_entry: DeviceEntry
) -> bool:
    return is_stale(
        device_entry.identifiers, entry.runtime_data.data, entry.entry_id, DOMAIN
    )


async def async_unload_entry(hass: HomeAssistant, entry: PulseConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
