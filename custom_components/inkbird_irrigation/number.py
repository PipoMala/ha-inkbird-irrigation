"""Number platform for Inkbird Irrigation — zone duration settings."""

from __future__ import annotations

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, NUM_ZONES
from .coordinator import InkbirdCoordinator
from .entity import InkbirdEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Inkbird duration number entities."""
    coordinator: InkbirdCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        InkbirdZoneDuration(coordinator, zone) for zone in range(1, NUM_ZONES + 1)
    )


class InkbirdZoneDuration(InkbirdEntity, NumberEntity):
    """Number entity for setting zone watering duration."""

    _attr_device_class = NumberDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_native_min_value = 1
    _attr_native_max_value = 240
    _attr_native_step = 1
    _attr_mode = NumberMode.BOX
    _attr_icon = "mdi:clock-time-four-outline"

    def __init__(self, coordinator: InkbirdCoordinator, zone: int) -> None:
        super().__init__(coordinator)
        self._zone = zone
        self._attr_unique_id = f"{DOMAIN}_{self._device_id}_zone_{zone}_duration"
        self._attr_name = f"Zone {zone} duration"

    @property
    def native_value(self) -> float:
        """Return the current duration setting."""
        val = self.coordinator.api.device.zone_duration.get(self._zone, 10)
        return max(val, 1)

    async def async_set_native_value(self, value: float) -> None:
        """Set the zone duration."""
        await self.hass.async_add_executor_job(
            self.coordinator.api.set_zone_duration, self._zone, int(value)
        )
        await self.coordinator.async_request_refresh()
