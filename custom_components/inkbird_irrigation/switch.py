"""Switch platform for Inkbird Irrigation — zone valves."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, NUM_ZONES
from .coordinator import InkbirdCoordinator
from .entity import InkbirdEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Inkbird zone switches."""
    coordinator: InkbirdCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        InkbirdZoneSwitch(coordinator, zone) for zone in range(1, NUM_ZONES + 1)
    )


class InkbirdZoneSwitch(InkbirdEntity, SwitchEntity):
    """Switch entity for an irrigation zone valve."""

    _attr_device_class = SwitchDeviceClass.SWITCH
    _attr_icon = "mdi:sprinkler-variant"

    def __init__(self, coordinator: InkbirdCoordinator, zone: int) -> None:
        super().__init__(coordinator)
        self._zone = zone
        self._attr_unique_id = f"{DOMAIN}_{self._device_id}_zone_{zone}"
        self._attr_translation_key = f"zone_{zone}"
        self._attr_name = f"Zone {zone}"

    @property
    def is_on(self) -> bool:
        """Return True if the zone valve is open."""
        # The device doesn't reliably report DP switch as True while running.
        # Use countdown > 0 as the active indicator instead.
        countdown = self.coordinator.api.device.zone_countdown.get(self._zone, 0)
        switch_state = self.coordinator.api.device.zone_active.get(self._zone, False)
        return switch_state or countdown > 0

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Open the zone valve."""
        await self.hass.async_add_executor_job(
            self.coordinator.api.turn_on_zone, self._zone
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Close the zone valve."""
        await self.hass.async_add_executor_job(
            self.coordinator.api.turn_off_zone, self._zone
        )
        await self.coordinator.async_request_refresh()
