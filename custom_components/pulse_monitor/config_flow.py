"""Config flow for Pulse."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_URL, CONF_VERIFY_SSL
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import PulseAuthError, PulseClient, PulseConnectionError
from .const import CONF_API_TOKEN, DOMAIN


class PulseConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            url_raw = user_input[CONF_URL].strip().rstrip("/")
            try:
                cv.url(url_raw)
            except vol.Invalid:
                errors["base"] = "invalid_url"
            else:
                url = url_raw.lower()
                await self.async_set_unique_id(url)
                self._abort_if_unique_id_configured()
                session = async_get_clientsession(self.hass, user_input[CONF_VERIFY_SSL])
                client = PulseClient(session, url, user_input[CONF_API_TOKEN])
                try:
                    await client.async_get_summary()
                except PulseAuthError:
                    errors["base"] = "invalid_auth"
                except PulseConnectionError:
                    errors["base"] = "cannot_connect"
                else:
                    return self.async_create_entry(
                        title="Pulse", data={**user_input, CONF_URL: url}
                    )

        schema = vol.Schema(
            {
                vol.Required(CONF_URL): str,
                vol.Required(CONF_API_TOKEN): str,
                vol.Required(CONF_VERIFY_SSL, default=True): bool,
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(schema, user_input),
            errors=errors,
        )
