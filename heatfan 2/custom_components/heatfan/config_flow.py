"""Config flow for Heatfan."""

from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import HeatfanApi, HeatfanAuthError, HeatfanConnectionError
from .const import CONF_REFRESH_TOKEN, CONF_UID, DOMAIN

_LOGGER = logging.getLogger(__name__)

USER_SCHEMA = vol.Schema(
    {vol.Required(CONF_EMAIL): str, vol.Required(CONF_PASSWORD): str}
)


class HeatfanConfigFlow(ConfigFlow, domain=DOMAIN):
    """Log in with the app.heatfan.eu account. Only the refresh token is stored."""

    VERSION = 1

    async def _login(self, email: str, password: str) -> tuple[dict[str, str], dict[str, Any] | None]:
        api = HeatfanApi(async_get_clientsession(self.hass))
        try:
            uid = await api.async_login(email, password)
        except HeatfanAuthError:
            return {"base": "invalid_auth"}, None
        except HeatfanConnectionError:
            return {"base": "cannot_connect"}, None
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Unexpected error logging in to Heatfan")
            return {"base": "unknown"}, None
        return {}, {CONF_EMAIL: email, CONF_UID: uid, CONF_REFRESH_TOKEN: api.refresh_token}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            errors, data = await self._login(user_input[CONF_EMAIL], user_input[CONF_PASSWORD])
            if data:
                await self.async_set_unique_id(data[CONF_UID])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=data[CONF_EMAIL], data=data)
        return self.async_show_form(step_id="user", data_schema=USER_SCHEMA, errors=errors)

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            errors, data = await self._login(entry.data[CONF_EMAIL], user_input[CONF_PASSWORD])
            if data:
                await self.async_set_unique_id(data[CONF_UID])
                self._abort_if_unique_id_mismatch(reason="wrong_account")
                return self.async_update_reload_and_abort(entry, data=data)
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}),
            description_placeholders={"email": entry.data[CONF_EMAIL]},
            errors=errors,
        )
