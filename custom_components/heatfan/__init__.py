"""The Heatfan integration (unofficial, via the Heatfan cloud)."""

from __future__ import annotations

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType
import homeassistant.helpers.config_validation as cv

from .api import HeatfanApi
from .const import CONF_REFRESH_TOKEN, CONF_UID, DOMAIN
from .coordinator import HeatfanConfigEntry, HeatfanCoordinator
from .services import async_setup_services

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    async_setup_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: HeatfanConfigEntry) -> bool:
    def _save_refresh_token(token: str) -> None:
        hass.config_entries.async_update_entry(
            entry, data={**entry.data, CONF_REFRESH_TOKEN: token}
        )

    api = HeatfanApi(
        async_get_clientsession(hass),
        refresh_token=entry.data[CONF_REFRESH_TOKEN],
        uid=entry.data[CONF_UID],
        on_refresh_token=_save_refresh_token,
    )
    coordinator = HeatfanCoordinator(hass, entry, api)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    coordinator.start_stream()
    return True


async def async_unload_entry(hass: HomeAssistant, entry: HeatfanConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
