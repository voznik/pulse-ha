"""Pulse binary sensors."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import helpers as h
from .coordinator import PulseConfigEntry
from .entity import PulseEntity


@dataclass(frozen=True, kw_only=True)
class PulseBinaryDescription(BinarySensorEntityDescription):
    value_fn: Callable[[Any], bool | None]
    attrs_fn: Callable[[Any], dict[str, Any]] | None = None


UPDATE_AVAILABLE = PulseBinaryDescription(
    key="update_available",
    translation_key="update_available",
    device_class=BinarySensorDeviceClass.UPDATE,
    value_fn=h.update_available,
)
OOM_KILLED = PulseBinaryDescription(
    key="oom_killed",
    translation_key="oom_killed",
    device_class=BinarySensorDeviceClass.PROBLEM,
    entity_category=EntityCategory.DIAGNOSTIC,
    value_fn=h.oom_killed,
)
ONLINE = PulseBinaryDescription(
    key="online",
    translation_key="online",
    device_class=BinarySensorDeviceClass.CONNECTIVITY,
    value_fn=h.is_online,
)
RUNNING = PulseBinaryDescription(
    key="running",
    translation_key="running",
    device_class=BinarySensorDeviceClass.RUNNING,
    value_fn=h.container_running,
    attrs_fn=h.container_attrs,
)
PROBLEM = PulseBinaryDescription(
    key="problem",
    translation_key="problem",
    device_class=BinarySensorDeviceClass.PROBLEM,
    value_fn=h.problem,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PulseConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    data = coordinator.data
    # Agents first so container via_device targets exist.
    entities = [PulseBinarySensor(coordinator, ONLINE, "agents", rid) for rid in data["agents"]]
    # ponytail: containers are fixed at setup; new ones need an integration reload.
    entities += [
        PulseBinarySensor(coordinator, d, "containers", rid)
        for rid in data["containers"]
        for d in (RUNNING, UPDATE_AVAILABLE, OOM_KILLED)
    ]
    entities.append(PulseBinarySensor(coordinator, PROBLEM, None, None))
    async_add_entities(entities)


class PulseBinarySensor(PulseEntity, BinarySensorEntity):
    entity_description: PulseBinaryDescription

    @property
    def is_on(self) -> bool | None:
        src = self.source
        return None if src is None else self.entity_description.value_fn(src)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        fn = self.entity_description.attrs_fn
        src = self.source
        return fn(src) if fn and src is not None else None
