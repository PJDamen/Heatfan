"""Serve the bundled heatfan-card and make sure every dashboard loads it."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import CoreState, Event, HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

CARD_FILE = "heatfan-card.js"
URL_BASE = f"/{DOMAIN}_static"
CARD_PATH = f"{URL_BASE}/{CARD_FILE}"
DATA_REGISTERED = f"{DOMAIN}_card_registered"


async def async_register_card(hass: HomeAssistant) -> None:
    """Expose the card and load it on every dashboard.

    Two mechanisms, because each has a gap on its own:
    - an extra frontend module: works for YAML dashboards, but a browser that
      loaded the page while Home Assistant was still starting misses it;
    - a dashboard resource (storage mode): loaded every time a dashboard opens.
    The card guards against being defined twice.
    """
    if hass.data.get(DATA_REGISTERED):
        return
    if "frontend" not in hass.config.components or hass.http is None:
        _LOGGER.debug("Frontend not loaded; heatfan-card not registered")
        return
    hass.data[DATA_REGISTERED] = True

    folder = Path(__file__).parent / "card"
    manifest = await hass.async_add_executor_job(
        (Path(__file__).parent / "manifest.json").read_text
    )
    version = json.loads(manifest).get("version", "0")
    url = f"{CARD_PATH}?v={version}"

    await hass.http.async_register_static_paths(
        [StaticPathConfig(URL_BASE, str(folder), cache_headers=True)]
    )
    add_extra_js_url(hass, url)

    async def _ensure_resource(_event: Event | None = None) -> None:
        try:
            await _async_ensure_lovelace_resource(hass, url)
        except Exception:  # noqa: BLE001 - never block setup over a card
            _LOGGER.debug("Could not register heatfan-card as dashboard resource", exc_info=True)

    if hass.state is CoreState.running:
        await _ensure_resource()
    else:
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _ensure_resource)


def _lovelace_part(data: Any, name: str) -> Any:
    if data is None:
        return None
    if isinstance(data, dict):
        return data.get(name)
    return getattr(data, name, None)


async def _async_ensure_lovelace_resource(hass: HomeAssistant, url: str) -> None:
    """Add or update our entry in the dashboard resources (storage mode only)."""
    lovelace = hass.data.get("lovelace")
    resources = _lovelace_part(lovelace, "resources")
    if resources is None or _lovelace_part(lovelace, "resource_mode") != "storage":
        return
    if not getattr(resources, "loaded", True):
        await resources.async_load()
        resources.loaded = True

    for item in resources.async_items():
        if str(item.get("url", "")).split("?")[0] == CARD_PATH:
            if item["url"] != url:
                await resources.async_update_item(item["id"], {"res_type": "module", "url": url})
                _LOGGER.debug("Updated heatfan-card resource to %s", url)
            return
    await resources.async_create_item({"res_type": "module", "url": url})
    _LOGGER.info("Added heatfan-card to dashboard resources")
