"""Config flow: email + password → cloud login → device count summary."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .auth import SmegAuth, SmegAuthError
from .const import CONF_ACCESS_TOKEN, CONF_IOT_USER_CODE, CONF_REFRESH_TOKEN, DOMAIN

_LOGGER = logging.getLogger(__name__)

_STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


class SmegConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the SmegConnect config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            session = async_get_clientsession(self.hass)
            try:
                tokens = await SmegAuth.login(
                    session,
                    user_input[CONF_USERNAME],
                    user_input[CONF_PASSWORD],
                )
            except SmegAuthError:
                errors["base"] = "invalid_auth"
            except aiohttp.ClientError as err:
                _LOGGER.exception("Smeg cloud connection error: %s", err)
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during Smeg login")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(tokens["iotUserCode"])
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"Devices registered on SmegConnect to {user_input[CONF_USERNAME]}",
                    data={
                        CONF_USERNAME: user_input[CONF_USERNAME],
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                        CONF_ACCESS_TOKEN: tokens["accessToken"],
                        CONF_REFRESH_TOKEN: tokens["refreshToken"],
                        CONF_IOT_USER_CODE: tokens["iotUserCode"],
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_STEP_USER_SCHEMA,
            errors=errors,
        )
