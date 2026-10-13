"""Fan-curve numbers for the active mode of a Heatfan unit."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.const import EntityCategory, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    DOMAIN,
    PARAM_MAX_SPEED,
    PARAM_MAX_TEMP,
    PARAM_START_SPEED,
    PARAM_START_TEMP,
    SPEED_MAX,
    SPEED_MIN,
    TEMP_MAX,
    TEMP_MIN,
)
from .coordinator import HeatfanConfigEntry, HeatfanCoordinator
from .entity import HeatfanEntity, setup_device_entities


@dataclass(frozen=True, kw_only=True)
class HeatfanNumberDescription(NumberEntityDescription):
    param: str
    # The partner value this one must stay below (start) or above (max).
    pair: str
    is_lower: bool


NUMBERS: tuple[HeatfanNumberDescription, ...] = (
    HeatfanNumberDescription(
        key="start_temp",
        translation_key="start_temp",
        param=PARAM_START_TEMP,
        pair=PARAM_MAX_TEMP,
        is_lower=True,
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=TEMP_MIN,
        native_max_value=TEMP_MAX,
        native_step=1,
    ),
    HeatfanNumberDescription(
        key="max_temp",
        translation_key="max_temp",
        param=PARAM_MAX_TEMP,
        pair=PARAM_START_TEMP,
        is_lower=False,
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=TEMP_MIN,
        native_max_value=TEMP_MAX,
        native_step=1,
    ),
    HeatfanNumberDescription(
        key="start_speed",
        translation_key="start_speed",
        param=PARAM_START_SPEED,
        pair=PARAM_MAX_SPEED,
        is_lower=True,
        native_min_value=SPEED_MIN,
        native_max_value=SPEED_MAX,
        native_step=1,
    ),
    HeatfanNumberDescription(
        key="max_speed",
        translation_key="max_speed",
        param=PARAM_MAX_SPEED,
        pair=PARAM_START_SPEED,
        is_lower=False,
        native_min_value=SPEED_MIN,
        native_max_value=SPEED_MAX,
        native_step=1,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HeatfanConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    setup_device_entities(
        entry,
        async_add_entities,
        lambda c, d: [HeatfanCurveNumber(c, d, desc) for desc in NUMBERS],
    )


class HeatfanCurveNumber(HeatfanEntity, NumberEntity):
    """A curve parameter of whichever mode is currently active."""

    entity_description: HeatfanNumberDescription
    _attr_mode = NumberMode.BOX
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self, coordinator: HeatfanCoordinator, device_id: str, description: HeatfanNumberDescription
    ) -> None:
        super().__init__(coordinator, device_id, description.key)
        self.entity_description = description

    def _active(self) -> tuple[int, dict] | None:
        unit = self.unit
        if not unit:
            return None
        mode = self.coordinator.current_mode(unit)
        if mode is None:
            return None
        return mode, self.coordinator.drive_params(unit).get(f"mode-{mode}") or {}

    @property
    def native_value(self) -> float | None:
        active = self._active()
        return active[1].get(self.entity_description.param) if active else None

    @property
    def extra_state_attributes(self) -> dict[str, int] | None:
        active = self._active()
        # Not "mode": that key is the number entity's own box/slider attribute.
        return {"active_mode": active[0]} if active else None

    async def async_set_native_value(self, value: float) -> None:
        active = self._active()
        if active is None:
            raise ServiceValidationError("Active mode unknown", translation_domain=DOMAIN)
        mode, params = active
        desc = self.entity_description
        pair = params.get(desc.pair)
        if pair is not None and ((desc.is_lower and value > pair) or (not desc.is_lower and value < pair)):
            raise ServiceValidationError(
                f"{desc.param} {int(value)} conflicts with {desc.pair} {pair}",
                translation_domain=DOMAIN,
                translation_key="curve_order",
                translation_placeholders={"param": desc.param, "pair": desc.pair, "value": str(pair)},
            )
        await self.coordinator.async_set_drive_param(self.device_id, mode, desc.param, int(value))
