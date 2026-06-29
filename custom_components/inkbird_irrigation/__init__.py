"""Inkbird IIC-600 WiFi Irrigation Controller integration for Home Assistant."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr
from homeassistant.const import Platform

from .api import InkbirdAPI
from .const import CONF_CLOUD_API_KEY, CONF_CLOUD_API_REGION, CONF_CLOUD_API_SECRET, CONF_DEVICE_ID, CONF_DEVICE_IP, CONF_DEVICE_NAME, CONF_LOCAL_KEY, DOMAIN
from .coordinator import InkbirdCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SWITCH,
    Platform.SENSOR,
    Platform.NUMBER,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Inkbird Irrigation from a config entry."""
    api = InkbirdAPI(
        entry.data[CONF_DEVICE_ID],
        entry.data[CONF_LOCAL_KEY],
        entry.data[CONF_DEVICE_IP],
        cloud_api_key=entry.data.get(CONF_CLOUD_API_KEY, ""),
        cloud_api_secret=entry.data.get(CONF_CLOUD_API_SECRET, ""),
        cloud_api_region=entry.data.get(CONF_CLOUD_API_REGION, "eu"),
    )

    connected = await hass.async_add_executor_job(api.connect)
    if not connected:
        # If cloud is available, allow setup anyway (cloud fallback will work)
        if api.has_cloud:
            cloud_ok = await hass.async_add_executor_job(api.enable_cloud_fallback)
            if not cloud_ok:
                raise ConfigEntryNotReady("Cannot connect to Inkbird IIC-600 (local and cloud both failed)")
            _LOGGER.warning("Local connection failed, starting with cloud fallback")
        else:
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
