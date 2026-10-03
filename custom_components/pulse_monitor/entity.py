"""Shared base entity."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import PulseCoordinator
from .helpers import container_image, display_name, get


class PulseEntity(CoordinatorEntity[PulseCoordinator]):
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: PulseCoordinator,
        description: EntityDescription,
        kind: str | None,
        rid: str | None,
    ) -> None:
        """kind is "agents", "containers" or None (fleet device)."""
        super().__init__(coordinator)
        self.entity_description = description
        self._kind = kind
        self._rid = rid
        entry_id = coordinator.config_entry.entry_id
        self._attr_unique_id = f"{entry_id}_{rid or 'fleet'}_{description.key}"
        data = coordinator.data
        if kind is None:
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, entry_id)}, name="Pulse", manufacturer="Pulse"
            )
            return
        res = data[kind][rid]
        info = DeviceInfo(
            identifiers={(DOMAIN, rid)},
            name=display_name(res) if kind == "agents" else rid,
            manufacturer="Pulse",
        )
        if kind == "agents":
            info["sw_version"] = get(res, "agent", "agentVersion")
            os_name = " ".join(
                p for p in (get(res, "agent", "osName"), get(res, "agent", "osVersion")) if p
            )
            info["model"] = os_name or None
        else:
            info["model"] = container_image(res) or "Docker container"
            parent = data["agents"].get(res.get("parentId"))
            if parent:
                # via_device_id needs a registry id; ensure the parent exists first.
                info["via_device_id"] = (
                    dr.async_get(coordinator.hass)
                    .async_get_or_create(
                        config_entry_id=entry_id,
                        identifiers={(DOMAIN, res["parentId"])},
                        name=display_name(parent),
                    )
                    .id
                )
        self._attr_device_info = info

    @property
    def source(self) -> Any:
        """Resource dict, or the whole data dict for the fleet device."""
        data = self.coordinator.data
        return data if self._kind is None else data[self._kind].get(self._rid)

    @property
    def available(self) -> bool:
        return super().available and self.source is not None
