"""Select platform for Inkbird Irrigation — operating mode."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, DP_MODE
from .coordinator import InkbirdCoordinator
from .entity import InkbirdEntity

MODE_OPTIONS = ["auto", "manual"]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Inkbird select entities."""
    coordinator: InkbirdCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([InkbirdModeSelect(coordinator)])


class InkbirdModeSelect(InkbirdEntity, SelectEntity):
    """Select the controller operating mode.

    In ``auto`` the controller runs its own internal programme (which can start
    zones on its own and conflict with schedules managed from Home Assistant).
    Set ``manual`` to let Home Assistant fully control the zones.
    """

    _attr_icon = "mdi:water-pump"
    _attr_options = MODE_OPTIONS

    def __init__(self, coordinator: InkbirdCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_{self._device_id}_mode_select"
        self._attr_name = "Mode"

    @property
    def current_option(self) -> str | None:
        """Return the current operating mode."""
        mode = self.coordinator.data.mode
        return mode if mode in MODE_OPTIONS else None

    async def async_select_option(self, option: str) -> None:
        """Set the operating mode."""
        if option not in MODE_OPTIONS:
            return
        await self.hass.async_add_executor_job(
            self.coordinator.api.set_dp, DP_MODE, option
        )
        self.coordinator.async_set_updated_data(self.coordinator.api.device.snapshot())
