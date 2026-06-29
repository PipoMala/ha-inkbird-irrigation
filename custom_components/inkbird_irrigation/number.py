"""Number platform for Inkbird Irrigation — zone duration settings."""

from __future__ import annotations

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberMode,
    RestoreNumber,
)
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

    entities: list[NumberEntity] = []
    for zone in range(1, NUM_ZONES + 1):
        entities.append(InkbirdZoneDuration(coordinator, zone))
    entities.append(InkbirdSeasonalAdjust(coordinator))

    async_add_entities(entities)


class InkbirdZoneDuration(InkbirdEntity, RestoreNumber):
    """Number entity for setting zone watering duration (used on next turn-on)."""

    _attr_device_class = NumberDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_native_min_value = 1
    _attr_native_max_value = 180
    _attr_native_step = 1
    _attr_mode = NumberMode.BOX
    _attr_icon = "mdi:clock-time-four-outline"

    def __init__(self, coordinator: InkbirdCoordinator, zone: int) -> None:
        super().__init__(coordinator)
        self._zone = zone
        self._attr_unique_id = f"{DOMAIN}_{self._device_id}_zone_{zone}_duration"
        self._attr_name = f"Zone {zone} duration"
        self._value: float = float(coordinator.zone_durations.get(zone, 30))

    @property
    def native_value(self) -> float:
        """Return the current duration setting."""
        return self._value

    async def async_added_to_hass(self) -> None:
        """Restore the last known value."""
        await super().async_added_to_hass()
        last = await self.async_get_last_number_data()
        if last is not None and last.native_value is not None:
            self._value = last.native_value
        self.coordinator.zone_durations[self._zone] = int(self._value)

    async def async_set_native_value(self, value: float) -> None:
        """Set the zone duration (used on next turn-on)."""
        self._value = value
        self.coordinator.zone_durations[self._zone] = int(value)
        self.async_write_ha_state()


class InkbirdSeasonalAdjust(InkbirdEntity, RestoreNumber):
    """Number entity for seasonal adjustment percentage."""

    _attr_native_unit_of_measurement = "%"
    _attr_native_min_value = 0
    _attr_native_max_value = 200
    _attr_native_step = 1
    _attr_mode = NumberMode.BOX
    _attr_icon = "mdi:leaf"

    def __init__(self, coordinator: InkbirdCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_{self._device_id}_seasonal_adjust"
        self._attr_name = "Seasonal adjustment"
        self._value: float = float(coordinator.seasonal_adjustment)

    @property
    def native_value(self) -> float:
        """Return the current seasonal adjustment."""
        return self._value

    async def async_added_to_hass(self) -> None:
        """Restore the last known value."""
        await super().async_added_to_hass()
        last = await self.async_get_last_number_data()
        if last is not None and last.native_value is not None:
            self._value = last.native_value
        self.coordinator.seasonal_adjustment = int(self._value)

    async def async_set_native_value(self, value: float) -> None:
        """Set the local seasonal adjustment."""
        self._value = value
        self.coordinator.seasonal_adjustment = int(value)
        self.async_write_ha_state()
