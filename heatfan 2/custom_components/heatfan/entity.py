"""Base entity for Heatfan units."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import HeatfanConfigEntry, HeatfanCoordinator


def setup_device_entities(
    entry: HeatfanConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
    factory: Callable[[HeatfanCoordinator, str], Iterable[Entity]],
) -> None:
    """Add entities for current units and for units that appear later."""
    coordinator = entry.runtime_data
    known: set[str] = set()

    @callback
    def _add_new() -> None:
        new = [d for d in coordinator.devices() if d not in known]
        if not new:
            return
        known.update(new)
        async_add_entities([e for d in new for e in factory(coordinator, d)])

    _add_new()
    entry.async_on_unload(coordinator.async_add_listener(_add_new))


class HeatfanEntity(CoordinatorEntity[HeatfanCoordinator]):
    """One entity belonging to one Heatfan unit (keyed by its MAC)."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: HeatfanCoordinator, device_id: str, key: str) -> None:
        super().__init__(coordinator)
        self.device_id = device_id
        self._attr_unique_id = f"{device_id}_{key}"
        _, unit = coordinator.device(device_id)  # type: ignore[misc]
        mac = ":".join(device_id[i : i + 2] for i in range(0, len(device_id), 2))
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            connections={("mac", mac.lower())},
            name=unit.get("deviceName") or device_id,
            manufacturer=MANUFACTURER,
            model="Heatfan Wi-Fi Controller",
            sw_version=unit.get("firmware-version"),
            hw_version=str(unit["hardware-version"]) if "hardware-version" in unit else None,
            serial_number=device_id,
        )

    @property
    def unit(self) -> dict[str, Any] | None:
        found = self.coordinator.device(self.device_id)
        return found[1] if found else None

    @property
    def available(self) -> bool:
        return super().available and self.unit is not None
