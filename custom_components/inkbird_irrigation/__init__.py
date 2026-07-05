"""Inkbird IIC-600 WiFi Irrigation Controller integration for Home Assistant."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr
from homeassistant.const import Platform

from .api import InkbirdAPI
from .const import CONF_DEVICE_ID, CONF_DEVICE_IP, CONF_DEVICE_NAME, CONF_LOCAL_KEY, DOMAIN
from .coordinator import InkbirdCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SWITCH,
    Platform.SENSOR,
    Platform.NUMBER,
    Platform.SELECT,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Inkbird Irrigation from a config entry."""
    api = InkbirdAPI(
        entry.data[CONF_DEVICE_ID],
        entry.data[CONF_LOCAL_KEY],
        entry.data[CONF_DEVICE_IP],
    )

    connected = await hass.async_add_executor_job(api.connect)
    if not connected:
        raise ConfigEntryNotReady("Cannot connect to Inkbird IIC-600")

    coordinator = InkbirdCoordinator(hass, api, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        coordinator: InkbirdCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await hass.async_add_executor_job(coordinator.api.disconnect)
    return unload_ok
