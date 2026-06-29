"""DataUpdateCoordinator for Inkbird Irrigation."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import InkbirdAPI, InkbirdDevice
from .const import NUM_ZONES

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=15)


class InkbirdCoordinator(DataUpdateCoordinator[InkbirdDevice]):
    """Coordinator for the Inkbird IIC-600."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: InkbirdAPI,
        entry: ConfigEntry,
    ) -> None:
        self.api = api
        self.entry = entry

        # User preferences (not stored on the device). Persisted by the
        # corresponding RestoreNumber entities and mirrored here so the switch
        # platform can read them without importing the number platform.
        self.zone_durations: dict[int, int] = {z: 30 for z in range(1, NUM_ZONES + 1)}
        self.seasonal_adjustment: int = 100

        super().__init__(
            hass,
            _LOGGER,
            name="Inkbird IIC-600",
            update_interval=SCAN_INTERVAL,
        )

    async def _async_update_data(self) -> InkbirdDevice:
        """Fetch latest state from the device."""
        device = await self.hass.async_add_executor_job(self._update)
        if device is None:
            reason = self.api.last_update_error or "unknown reason"
            raise UpdateFailed(f"Failed to fetch state from Inkbird IIC-600: {reason}")
        return device

    def _update(self) -> InkbirdDevice | None:
        """Poll the device and return a consistent snapshot (runs in executor)."""
        if self.api.update():
            return self.api.device.snapshot()
        return None
