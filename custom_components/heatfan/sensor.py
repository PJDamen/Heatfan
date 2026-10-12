"""Sensors for Heatfan units."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import HeatfanConfigEntry, HeatfanCoordinator
from .entity import HeatfanEntity, setup_device_entities


def _status(key: str) -> Callable[[dict[str, Any]], Any]:
    return lambda unit: (unit.get("status") or {}).get(key)


def _round(key: str, digits: int) -> Callable[[dict[str, Any]], Any]:
    def _get(unit: dict[str, Any]) -> Any:
        value = _status(key)(unit)
        return round(float(value), digits) if value is not None else None

    return _get


def _last_seen(unit: dict[str, Any]) -> datetime | None:
    ts = _status("timestamp")(unit)
    return datetime.fromtimestamp(int(ts), tz=timezone.utc) if ts else None


@dataclass(frozen=True, kw_only=True)
class HeatfanSensorDescription(SensorEntityDescription):
    value_fn: Callable[[dict[str, Any]], Any]


SENSORS: tuple[HeatfanSensorDescription, ...] = (
    HeatfanSensorDescription(
        key="radiator_temperature",
        translation_key="radiator_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
        value_fn=_round("temp_ext", 2),
    ),
    HeatfanSensorDescription(
        key="fan_speed",
        translation_key="fan_speed",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_status("speed"),
    ),
    HeatfanSensorDescription(
        key="temperature_trend",
        translation_key="temperature_trend",
        device_class=SensorDeviceClass.ENUM,
        options=["rising", "falling", "stable"],
        value_fn=lambda unit: (
            v if (v := _status("temp_slope")(unit)) in ("rising", "falling", "stable") else None
        ),
    ),
    HeatfanSensorDescription(
        key="last_seen",
        translation_key="last_seen",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_last_seen,
    ),
    HeatfanSensorDescription(
        key="board_temperature",
        translation_key="board_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=_round("temp_board", 2),
    ),
    HeatfanSensorDescription(
        key="mcu_temperature",
        translation_key="mcu_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=_round("temp_mcu", 2),
    ),
    HeatfanSensorDescription(
        key="rssi",
        translation_key="rssi",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_status("rssi"),
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
        lambda c, d: [HeatfanSensor(c, d, desc) for desc in SENSORS],
    )


class HeatfanSensor(HeatfanEntity, SensorEntity):
    entity_description: HeatfanSensorDescription

    def __init__(
        self, coordinator: HeatfanCoordinator, device_id: str, description: HeatfanSensorDescription
    ) -> None:
        super().__init__(coordinator, device_id, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        unit = self.unit
        return self.entity_description.value_fn(unit) if unit else None
