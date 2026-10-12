"""Mode select for Heatfan units."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import MODES
from .coordinator import HeatfanConfigEntry
from .entity import HeatfanEntity, setup_device_entities

OPTIONS = [f"mode_{m}" for m in MODES]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HeatfanConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    setup_device_entities(
        entry, async_add_entities, lambda c, d: [HeatfanModeSelect(c, d, "mode")]
    )


class HeatfanModeSelect(HeatfanEntity, SelectEntity):
    _attr_translation_key = "mode"
    _attr_options = OPTIONS

    @property
    def current_option(self) -> str | None:
        unit = self.unit
        mode = self.coordinator.current_mode(unit) if unit else None
        return f"mode_{mode}" if mode in MODES else None

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_set_mode(self.device_id, int(option.removeprefix("mode_")))
