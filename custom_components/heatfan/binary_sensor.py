"""Connectivity sensor for Heatfan units."""

from __future__ import annotations

from datetime import datetime, timezone

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import OFFLINE_AFTER
from .coordinator import HeatfanConfigEntry
from .entity import HeatfanEntity, setup_device_entities


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HeatfanConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    setup_device_entities(
        entry, async_add_entities, lambda c, d: [HeatfanOnline(c, d, "online")]
    )


class HeatfanOnline(HeatfanEntity, BinarySensorEntity):
    """On when the unit reported a status within OFFLINE_AFTER."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def is_on(self) -> bool | None:
        unit = self.unit
        ts = (unit or {}).get("status", {}).get("timestamp")
        if not ts:
            return None
        age = datetime.now(timezone.utc) - datetime.fromtimestamp(int(ts), tz=timezone.utc)
        return age < OFFLINE_AFTER
