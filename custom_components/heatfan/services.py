"""Services for Heatfan."""

from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv, device_registry as dr

from .const import (
    DOMAIN,
    MODES,
    PARAM_MAX_SPEED,
    PARAM_MAX_TEMP,
    PARAM_START_SPEED,
    PARAM_START_TEMP,
    SPEED_MAX,
    SPEED_MIN,
    TEMP_MAX,
    TEMP_MIN,
)

SERVICE_SET_DRIVE_PARAMS = "set_drive_params"

_TEMP = vol.All(vol.Coerce(int), vol.Range(min=TEMP_MIN, max=TEMP_MAX))
_SPEED = vol.All(vol.Coerce(int), vol.Range(min=SPEED_MIN, max=SPEED_MAX))

SCHEMA = vol.Schema(
    {
        vol.Required("device_id"): vol.All(cv.ensure_list, [cv.string]),
        vol.Optional("mode"): vol.All(vol.Coerce(int), vol.In(MODES)),
        vol.Optional("start_temp"): _TEMP,
        vol.Optional("max_temp"): _TEMP,
        vol.Optional("start_speed"): _SPEED,
        vol.Optional("max_speed"): _SPEED,
    }
)

_FIELDS = {
    "start_temp": PARAM_START_TEMP,
    "max_temp": PARAM_MAX_TEMP,
    "start_speed": PARAM_START_SPEED,
    "max_speed": PARAM_MAX_SPEED,
}


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    async def _set_drive_params(call: ServiceCall) -> None:
        values = {_FIELDS[k]: v for k, v in call.data.items() if k in _FIELDS}
        if not values:
            raise ServiceValidationError("Give at least one curve value")
        registry = dr.async_get(hass)
        for ha_device_id in call.data["device_id"]:
            device = registry.async_get(ha_device_id)
            heatfan_id = next(
                (i for d, i in (device.identifiers if device else ()) if d == DOMAIN), None
            )
            if heatfan_id is None:
                raise ServiceValidationError(f"{ha_device_id} is not a Heatfan unit")
            coordinator = None
            for entry_id in device.config_entries:
                entry = hass.config_entries.async_get_entry(entry_id)
                if entry and entry.domain == DOMAIN and entry.state is ConfigEntryState.LOADED:
                    coordinator = entry.runtime_data
            if coordinator is None:
                raise ServiceValidationError("Heatfan integration not loaded")
            found = coordinator.device(heatfan_id)
            if found is None:
                raise ServiceValidationError(f"Heatfan unit {heatfan_id} not found")
            unit = found[1]
            mode = call.data.get("mode") or coordinator.current_mode(unit)
            current = coordinator.drive_params(unit).get(f"mode-{mode}") or {}
            merged = {**current, **values}
            for low, high in ((PARAM_START_TEMP, PARAM_MAX_TEMP), (PARAM_START_SPEED, PARAM_MAX_SPEED)):
                if low in merged and high in merged and merged[low] > merged[high]:
                    raise ServiceValidationError(f"{low} ({merged[low]}) is above {high} ({merged[high]})")
            await coordinator.async_set_drive_params(heatfan_id, mode, values)

    hass.services.async_register(DOMAIN, SERVICE_SET_DRIVE_PARAMS, _set_drive_params, schema=SCHEMA)
