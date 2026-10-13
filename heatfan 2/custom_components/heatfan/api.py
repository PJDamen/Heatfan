"""Client for the (unofficial) Heatfan cloud, which is a Firebase backend."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable
import json
import logging
import time
from typing import Any
from urllib.parse import quote

import aiohttp

from .const import (
    FIREBASE_API_KEY,
    FIREBASE_DB_URL,
    REFRESH_URL,
    ROOT_PATH,
    SIGN_IN_URL,
)

_LOGGER = logging.getLogger(__name__)

_INVALID_AUTH_CODES = {
    "INVALID_LOGIN_CREDENTIALS",
    "INVALID_PASSWORD",
    "EMAIL_NOT_FOUND",
    "USER_DISABLED",
    "INVALID_REFRESH_TOKEN",
    "TOKEN_EXPIRED",
    "USER_NOT_FOUND",
    "INVALID_EMAIL",
}


class HeatfanError(Exception):
    """Generic Heatfan error."""


class HeatfanAuthError(HeatfanError):
    """Credentials or refresh token are no longer valid."""


class HeatfanConnectionError(HeatfanError):
    """Could not reach the Heatfan cloud."""


def _seg(value: str) -> str:
    """Encode one database path segment (room names can contain spaces)."""
    return quote(str(value), safe="")


def device_path(room: str, device_id: str) -> str:
    """Relative path of a device below the user's live-data node."""
    return f"room/{_seg(room)}/{_seg(device_id)}"


class HeatfanApi:
    """Thin async wrapper around Firebase Auth + Realtime Database REST."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        refresh_token: str | None = None,
        uid: str | None = None,
        on_refresh_token: Callable[[str], None] | None = None,
    ) -> None:
        self._session = session
        self._refresh_token = refresh_token
        self.uid = uid
        self._id_token: str | None = None
        self._expires_at = 0.0
        self._on_refresh_token = on_refresh_token
        self._lock = asyncio.Lock()

    @property
    def refresh_token(self) -> str | None:
        return self._refresh_token

    # ------------------------------------------------------------------ auth
    async def async_login(self, email: str, password: str) -> str:
        """Sign in with e-mail/password. Returns the Firebase uid."""
        data = await self._post_json(
            SIGN_IN_URL,
            json_body={
                "email": email,
                "password": password,
                "returnSecureToken": True,
            },
        )
        self._store_tokens(
            data["idToken"], data["refreshToken"], int(data["expiresIn"])
        )
        self.uid = data["localId"]
        return self.uid

    async def async_get_token(self) -> str:
        """Return a valid ID token, refreshing it when it is about to expire."""
        async with self._lock:
            if self._id_token and time.monotonic() < self._expires_at - 300:
                return self._id_token
            if not self._refresh_token:
                raise HeatfanAuthError("No refresh token available")
            data = await self._post_json(
                REFRESH_URL,
                form_body={
                    "grant_type": "refresh_token",
                    "refresh_token": self._refresh_token,
                },
            )
            self._store_tokens(
                data["id_token"], data["refresh_token"], int(data["expires_in"])
            )
            self.uid = data.get("user_id", self.uid)
            return self._id_token  # type: ignore[return-value]

    def _store_tokens(self, id_token: str, refresh: str, expires_in: int) -> None:
        self._id_token = id_token
        self._expires_at = time.monotonic() + expires_in
        if refresh != self._refresh_token:
            self._refresh_token = refresh
            if self._on_refresh_token:
                self._on_refresh_token(refresh)

    async def _post_json(
        self,
        url: str,
        json_body: dict[str, Any] | None = None,
        form_body: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        try:
            async with self._session.post(
                url,
                params={"key": FIREBASE_API_KEY},
                json=json_body,
                data=form_body,
                timeout=aiohttp.ClientTimeout(total=20),
            ) as resp:
                data = await resp.json(content_type=None)
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise HeatfanConnectionError(str(err)) from err
        if resp.status >= 400:
            message = str((data or {}).get("error", {}).get("message", ""))
            code = message.split(" ")[0].split(":")[0]
            if code in _INVALID_AUTH_CODES or resp.status in (400, 401, 403):
                raise HeatfanAuthError(message or f"HTTP {resp.status}")
            raise HeatfanError(message or f"HTTP {resp.status}")
        return data

    # ------------------------------------------------------------- database
    def _url(self, rel_path: str = "") -> str:
        base = f"{FIREBASE_DB_URL}/{ROOT_PATH}/{_seg(self.uid or '')}"
        if rel_path:
            base = f"{base}/{rel_path.strip('/')}"
        return f"{base}.json"

    async def _request(
        self, method: str, rel_path: str = "", body: Any = None
    ) -> Any:
        token = await self.async_get_token()
        try:
            async with self._session.request(
                method,
                self._url(rel_path),
                params={"auth": token},
                json=body,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                if resp.status in (401, 403):
                    raise HeatfanAuthError(f"Database refused access ({resp.status})")
                if resp.status >= 400:
                    raise HeatfanError(
                        f"{method} {rel_path} failed: HTTP {resp.status} "
                        f"{await resp.text()}"
                    )
                return await resp.json(content_type=None)
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise HeatfanConnectionError(str(err)) from err

    async def async_get_live_data(self) -> dict[str, Any]:
        """Full live-data tree for this account."""
        return await self._request("GET") or {}

    async def async_patch(self, rel_path: str, values: dict[str, Any]) -> None:
        await self._request("PATCH", rel_path, values)

    async def async_put(self, rel_path: str, value: Any) -> None:
        await self._request("PUT", rel_path, value)

    # -------------------------------------------------------------- stream
    async def async_stream(
        self, on_event: Callable[[str, dict[str, Any]], Awaitable[None] | None]
    ) -> None:
        """Open a Firebase SSE stream and feed put/patch events to on_event.

        Returns normally when the server ends the stream (e.g. auth_revoked
        once the hour-long ID token expires), so the caller can reconnect.
        """
        token = await self.async_get_token()
        try:
            async with self._session.get(
                self._url(),
                params={"auth": token},
                headers={"Accept": "text/event-stream"},
                timeout=aiohttp.ClientTimeout(total=None, sock_read=90),
            ) as resp:
                if resp.status in (401, 403):
                    raise HeatfanAuthError(f"Stream refused ({resp.status})")
                if resp.status >= 400:
                    raise HeatfanError(f"Stream failed: HTTP {resp.status}")
                async for event, data in parse_sse(resp.content):
                    if event in ("put", "patch"):
                        result = on_event(event, data)
                        if asyncio.iscoroutine(result):
                            await result
                    elif event in ("cancel", "auth_revoked"):
                        _LOGGER.debug("Heatfan stream ended by server: %s", event)
                        return
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise HeatfanConnectionError(str(err)) from err


async def parse_sse(
    content: AsyncIterator[bytes],
) -> AsyncIterator[tuple[str, dict[str, Any]]]:
    """Parse a text/event-stream body into (event, json-data) tuples."""
    event: str | None = None
    data_lines: list[str] = []
    async for raw in content:
        line = raw.decode("utf-8").rstrip("\r\n")
        if not line:
            if event and data_lines:
                payload = "\n".join(data_lines)
                try:
                    parsed = json.loads(payload)
                except ValueError:
                    parsed = None
                yield event, parsed if isinstance(parsed, dict) else {"data": parsed}
            event, data_lines = None, []
            continue
        if line.startswith("event:"):
            event = line[6:].strip()
        elif line.startswith("data:"):
            data_lines.append(line[5:].lstrip())
