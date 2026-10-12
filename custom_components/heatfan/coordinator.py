"""Data coordinator: keeps a local mirror of the Heatfan live-data tree."""

from __future__ import annotations

import asyncio
import copy
from dataclasses import dataclass
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    HeatfanApi,
    HeatfanAuthError,
    HeatfanConnectionError,
    HeatfanError,
    device_path,
)
from .const import DOMAIN, POLL_INTERVAL

_LOGGER = logging.getLogger(__name__)

type HeatfanConfigEntry = ConfigEntry[HeatfanCoordinator]


@dataclass(frozen=True)
class DeviceRef:
    """Where a unit lives in the tree; the room can change, the id cannot."""

    room: str
    device_id: str


def apply_event(tree: dict[str, Any], event: str, path: str, data: Any) -> dict[str, Any]:
    """Apply a Firebase put/patch event to a nested dict and return the result."""
    parts = [p for p in path.split("/") if p]
    if not parts:
        if event == "put":
            return data if isinstance(data, dict) else {}
        merged = dict(tree)
        for key, value in (data or {}).items():
            _set_path(merged, [p for p in key.split("/") if p], value)
        return merged

    tree = dict(tree)
    if event == "put":
        _set_path(tree, parts, data)
    else:
        for key, value in (data or {}).items():
            _set_path(tree, parts + [p for p in key.split("/") if p], value)
    return tree


def _set_path(tree: dict[str, Any], parts: list[str], value: Any) -> None:
    node = tree
    for part in parts[:-1]:
        child = node.get(part)
        child = dict(child) if isinstance(child, dict) else {}
        node[part] = child
        node = child
    if value is None:
        node.pop(parts[-1], None)
    else:
        node[parts[-1]] = value


class HeatfanCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Polls as fallback, but mostly listens to the Firebase event stream."""

    config_entry: HeatfanConfigEntry

    def __init__(self, hass: HomeAssistant, entry: HeatfanConfigEntry, api: HeatfanApi) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=POLL_INTERVAL,
        )
        self.api = api
        self._stream_task: asyncio.Task | None = None

    # ------------------------------------------------------------- refresh
    async def _async_update_data(self) -> dict[str, Any]:
        try:
            return await self.api.async_get_live_data()
        except HeatfanAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except HeatfanError as err:
            raise UpdateFailed(str(err)) from err

    # -------------------------------------------------------------- stream
    def start_stream(self) -> None:
        self._stream_task = self.config_entry.async_create_background_task(
            self.hass, self._stream_loop(), f"{DOMAIN}_stream"
        )

    async def _stream_loop(self) -> None:
        backoff = 5
        while True:
            try:
                await self.api.async_stream(self._handle_event)
                backoff = 5  # normal end (token expiry) -> reconnect at once
                continue
            except HeatfanAuthError:
                # Token might simply be stale; a full refresh decides whether
                # the credentials are really gone (that triggers reauth).
                await self.async_request_refresh()
            except HeatfanConnectionError as err:
                _LOGGER.debug("Heatfan stream dropped: %s", err)
            except HeatfanError as err:
                _LOGGER.warning("Heatfan stream error: %s", err)
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 300)

    def _handle_event(self, event: str, payload: dict[str, Any]) -> None:
        path = payload.get("path", "/")
        new = apply_event(self.data or {}, event, path, payload.get("data"))
        self.async_set_updated_data(new)

    # ------------------------------------------------------------- helpers
    def devices(self) -> dict[str, DeviceRef]:
        """All units, keyed by device id (MAC)."""
        result: dict[str, DeviceRef] = {}
        for room, units in ((self.data or {}).get("room") or {}).items():
            if not isinstance(units, dict):
                continue
            for device_id, unit in units.items():
                if isinstance(unit, dict):
                    result[device_id] = DeviceRef(room, device_id)
        return result

    def device(self, device_id: str) -> tuple[DeviceRef, dict[str, Any]] | None:
        ref = self.devices().get(device_id)
        if ref is None:
            return None
        return ref, self.data["room"][ref.room][device_id]

    @staticmethod
    def current_mode(unit: dict[str, Any]) -> int | None:
        user = unit.get("user") or {}
        mode = user.get("mode", unit.get("mode"))
        return int(mode) if mode is not None else None

    @staticmethod
    def drive_params(unit: dict[str, Any]) -> dict[str, Any]:
        user = unit.get("user") or {}
        return user.get("drive-params") or unit.get("drive-params") or {}

    # -------------------------------------------------------------- writes
    async def async_set_mode(self, device_id: str, mode: int) -> None:
        found = self._require(device_id)
        ref, unit = found
        base = device_path(ref.room, ref.device_id)
        if (unit.get("user") or {}).get("mode") is not None:
            rel, key_path = f"{base}/user", ["user", "mode"]
        else:  # same fallback the web dashboard uses
            rel, key_path = base, ["mode"]
        await self._write(self.api.async_patch(rel, {"mode": mode}))
        self._optimistic(ref, key_path, mode)

    async def async_set_drive_param(
        self, device_id: str, mode: int, param: str, value: int
    ) -> None:
        ref, unit = self._require(device_id)
        base = device_path(ref.room, ref.device_id)
        if (unit.get("user") or {}).get("drive-params") is not None:
            rel = f"{base}/user/drive-params/mode-{mode}"
            key_path = ["user", "drive-params", f"mode-{mode}", param]
        else:
            rel = f"{base}/drive-params/mode-{mode}"
            key_path = ["drive-params", f"mode-{mode}", param]
        await self._write(self.api.async_patch(rel, {param: value}))
        self._optimistic(ref, key_path, value)

    async def async_set_drive_params(
        self, device_id: str, mode: int, values: dict[str, int]
    ) -> None:
        """Write several curve values of one mode in a single PATCH."""
        ref, unit = self._require(device_id)
        base = device_path(ref.room, ref.device_id)
        if (unit.get("user") or {}).get("drive-params") is not None:
            rel, prefix = f"{base}/user/drive-params/mode-{mode}", ["user", "drive-params"]
        else:
            rel, prefix = f"{base}/drive-params/mode-{mode}", ["drive-params"]
        await self._write(self.api.async_patch(rel, values))
        for param, value in values.items():
            self._optimistic(ref, [*prefix, f"mode-{mode}", param], value)

    def _require(self, device_id: str) -> tuple[DeviceRef, dict[str, Any]]:
        found = self.device(device_id)
        if found is None:
            raise HomeAssistantError(f"Heatfan unit {device_id} not found")
        return found

    async def _write(self, coro) -> None:
        try:
            await coro
        except HeatfanAuthError as err:
            self.config_entry.async_start_reauth(self.hass)
            raise HomeAssistantError(f"Heatfan login expired: {err}") from err
        except HeatfanError as err:
            raise HomeAssistantError(f"Heatfan write failed: {err}") from err

    def _optimistic(self, ref: DeviceRef, key_path: list[str], value: Any) -> None:
        data = copy.deepcopy(self.data)
        _set_path(data["room"][ref.room][ref.device_id], key_path, value)
        self.async_set_updated_data(data)
