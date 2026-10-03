"""Pulse sensors."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfDataRate, UnitOfInformation
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from . import helpers as h
from .coordinator import PulseConfigEntry
from .entity import PulseEntity


@dataclass(frozen=True, kw_only=True)
class PulseSensorDescription(SensorEntityDescription):
    # Receives the resource dict (agents/containers) or the full data dict (fleet).
    value_fn: Callable[[Any], Any]
    attrs_fn: Callable[[Any], dict[str, Any]] | None = None


_PCT = {
    "native_unit_of_measurement": PERCENTAGE,
    "state_class": SensorStateClass.MEASUREMENT,
    "suggested_display_precision": 1,
}
_SIZE = {
    "device_class": SensorDeviceClass.DATA_SIZE,
    "native_unit_of_measurement": UnitOfInformation.BYTES,
    "suggested_unit_of_measurement": UnitOfInformation.GIBIBYTES,
    "suggested_display_precision": 2,
    "state_class": SensorStateClass.MEASUREMENT,
}
_RATE = {
    "device_class": SensorDeviceClass.DATA_RATE,
    "native_unit_of_measurement": UnitOfDataRate.BYTES_PER_SECOND,
    "suggested_unit_of_measurement": UnitOfDataRate.KIBIBYTES_PER_SECOND,
    "suggested_display_precision": 1,
    "state_class": SensorStateClass.MEASUREMENT,
}

AGENT_SENSORS = (
    PulseSensorDescription(key="cpu", translation_key="cpu", value_fn=h.cpu, **_PCT),
    PulseSensorDescription(key="memory", translation_key="memory", value_fn=h.mem_pct, **_PCT),
    PulseSensorDescription(key="memory_used", translation_key="memory_used", value_fn=h.mem_used, **_SIZE),
    PulseSensorDescription(key="disk", translation_key="disk", value_fn=h.disk_pct, **_PCT),
    PulseSensorDescription(key="disk_used", translation_key="disk_used", value_fn=h.disk_used, **_SIZE),
    PulseSensorDescription(
        key="load",
        translation_key="load",
        value_fn=h.load_pct,
        attrs_fn=h.load_attrs,
        **_PCT,
    ),
    PulseSensorDescription(key="net_in", translation_key="net_in", value_fn=h.net_in, **_RATE),
    PulseSensorDescription(key="net_out", translation_key="net_out", value_fn=h.net_out, **_RATE),
    PulseSensorDescription(key="disk_read", translation_key="disk_read", value_fn=h.disk_read, **_RATE),
    PulseSensorDescription(key="disk_write", translation_key="disk_write", value_fn=h.disk_write, **_RATE),
    PulseSensorDescription(
        key="boot_time",
        translation_key="boot_time",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda r: h.boot_time(r, dt_util.utcnow()),
    ),
    PulseSensorDescription(
        key="package_updates",
        translation_key="package_updates",
        value_fn=h.package_updates,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    PulseSensorDescription(
        key="health",
        translation_key="health",
        device_class=SensorDeviceClass.ENUM,
        options=list(h.VERDICTS),
        value_fn=h.verdict,
    ),
)

_OFF = {"entity_registry_enabled_default": False}

CONTAINER_SENSORS = (
    PulseSensorDescription(key="cpu", translation_key="cpu", value_fn=h.cpu, **_PCT),
    PulseSensorDescription(key="memory", translation_key="memory", value_fn=h.mem_pct, **_PCT),
    PulseSensorDescription(
        key="health",
        translation_key="container_health",
        device_class=SensorDeviceClass.ENUM,
        options=list(h.CONTAINER_HEALTH),
        value_fn=h.container_health,
    ),
    PulseSensorDescription(
        key="started",
        translation_key="started",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=h.started,
    ),
    PulseSensorDescription(key="memory_used", translation_key="memory_used", value_fn=h.mem_used, **_SIZE, **_OFF),
    PulseSensorDescription(key="net_in", translation_key="net_in", value_fn=h.net_in, **_RATE, **_OFF),
    PulseSensorDescription(key="net_out", translation_key="net_out", value_fn=h.net_out, **_RATE, **_OFF),
    PulseSensorDescription(key="disk_read", translation_key="disk_read", value_fn=h.disk_read, **_RATE, **_OFF),
    PulseSensorDescription(key="disk_write", translation_key="disk_write", value_fn=h.disk_write, **_RATE, **_OFF),
)

FLEET_SENSORS = (
    PulseSensorDescription(
        key="active_alerts",
        translation_key="active_alerts",
        value_fn=h.alert_count,
        attrs_fn=h.alert_attrs,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    PulseSensorDescription(
        key="containers_running",
        translation_key="containers_running",
        value_fn=h.containers_running,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    PulseSensorDescription(
        key="containers_unhealthy",
        translation_key="containers_unhealthy",
        value_fn=h.containers_unhealthy,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    PulseSensorDescription(
        key="container_updates",
        translation_key="container_updates",
        value_fn=h.container_updates,
        attrs_fn=h.container_update_attrs,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    *(
        PulseSensorDescription(
            key=f"verdict_{v}",
            translation_key=f"verdict_{v}",
            value_fn=lambda d, v=v: h.verdict_count(d, v),
            state_class=SensorStateClass.MEASUREMENT,
        )
        for v in h.VERDICTS
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PulseConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    data = coordinator.data
    entities: list[PulseSensor] = [
        PulseSensor(coordinator, d, "agents", rid)
        for rid in data["agents"]
        for d in AGENT_SENSORS
    ]
    # ponytail: containers are fixed at setup; new ones need an integration reload.
    entities += [
        PulseSensor(coordinator, d, "containers", rid)
        for rid in data["containers"]
        for d in CONTAINER_SENSORS
    ]
    entities += [PulseSensor(coordinator, d, None, None) for d in FLEET_SENSORS]
    async_add_entities(entities)


class PulseSensor(PulseEntity, SensorEntity):
    entity_description: PulseSensorDescription
    _boot: datetime | None = None

    @property
    def native_value(self) -> Any:
        src = self.source
        if src is None:
            return None
        value = self.entity_description.value_fn(src)
        if isinstance(value, datetime):
            # Uptime-derived boot time jitters each poll; hold it steady.
            value = self._boot = h.stable(self._boot, value)
        return value

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        fn = self.entity_description.attrs_fn
        src = self.source
        return fn(src) if fn and src is not None else None
