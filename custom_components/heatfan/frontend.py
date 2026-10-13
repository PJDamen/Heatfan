"""Serve the bundled heatfan-card and load it on every dashboard."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

CARD_FILE = "heatfan-card.js"
URL_BASE = f"/{DOMAIN}_static"
DATA_REGISTERED = f"{DOMAIN}_card_registered"


async def async_register_card(hass: HomeAssistant) -> None:
    """Expose the card at /heatfan_static/heatfan-card.js and add it to the frontend."""
    if hass.data.get(DATA_REGISTERED):
        return
    if "frontend" not in hass.config.components or hass.http is None:
        _LOGGER.debug("Frontend not loaded; heatfan-card not registered")
        return

    folder = Path(__file__).parent / "card"
    manifest = await hass.async_add_executor_job(
        (Path(__file__).parent / "manifest.json").read_text
    )
    version = json.loads(manifest).get("version", "0")

    await hass.http.async_register_static_paths(
        [StaticPathConfig(URL_BASE, str(folder), cache_headers=True)]
    )
    # Version in the query string so browsers fetch the new card after an update.
    add_extra_js_url(hass, f"{URL_BASE}/{CARD_FILE}?v={version}")
    hass.data[DATA_REGISTERED] = True
