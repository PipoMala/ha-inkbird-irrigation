"""Config flow for Inkbird Irrigation."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow
from homeassistant.data_entry_flow import FlowResult

from .api import InkbirdAPI
from .const import CONF_DEVICE_ID, CONF_DEVICE_IP, CONF_DEVICE_NAME, CONF_LOCAL_KEY, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_DEVICE_NAME, default="Inkbird IIC-600"): str,
        vol.Required(CONF_DEVICE_ID): str,
        vol.Required(CONF_LOCAL_KEY): str,
        vol.Required(CONF_DEVICE_IP): str,
    }
)


class InkbirdIrrigationConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Inkbird Irrigation."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Test connection
            api = InkbirdAPI(
                user_input[CONF_DEVICE_ID],
                user_input[CONF_LOCAL_KEY],
                user_input[CONF_DEVICE_IP],
            )
            connected = await self.hass.async_add_executor_job(api.connect)

            if connected:
                # Check for duplicate
                await self.async_set_unique_id(user_input[CONF_DEVICE_ID])
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=user_input[CONF_DEVICE_NAME],
                    data=user_input,
                )
            else:
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
