"""Switch platform for Inkbird Irrigation — zone valves."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    DP_POWER_SWITCH,
    DP_RAIN_SENSOR_ENABLED,
    DP_SKIP_SCHEDULE,
    DP_SYSTEM_POWER,
    NUM_ZONES,
)
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
    
    entities: list[SwitchEntity] = []
    
    # Zone switches
    for zone in range(1, NUM_ZONES + 1):
        entities.append(InkbirdZoneSwitch(coordinator, zone))
    
    # System switches
    entities.append(InkbirdMainValveSwitch(coordinator))
    entities.append(InkbirdPowerSwitch(coordinator))
    entities.append(InkbirdRainSensorSwitch(coordinator))
    entities.append(InkbirdSkipScheduleSwitch(coordinator))
    
    async_add_entities(entities)


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
        """Return True if the zone valve is open.

        The per-zone switch DP is the single source of truth for zone state.
        """
        return self.coordinator.data.zone_active.get(self._zone, False)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Open the zone valve for the configured duration.

        The duration is used verbatim. Any seasonal scaling is applied on the HA
        side (by the schedule automation or the card) before this is called, so
        the integration never re-scales it and never writes the device seasonal
        DP.
        """
        duration = self.coordinator.zone_durations.get(self._zone, 30)
        _LOGGER.debug("Zone %d turn_on with duration=%d min", self._zone, duration)
        await self.hass.async_add_executor_job(
            self.coordinator.api.turn_on_zone, self._zone, duration
        )
        self.coordinator.async_set_updated_data(self.coordinator.api.device.snapshot())

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Close the zone valve."""
        await self.hass.async_add_executor_job(
            self.coordinator.api.turn_off_zone, self._zone
        )
        self.coordinator.async_set_updated_data(self.coordinator.api.device.snapshot())


class InkbirdMainValveSwitch(InkbirdEntity, SwitchEntity):
    """Switch for the main valve control."""

    _attr_icon = "mdi:valve"

    def __init__(self, coordinator: InkbirdCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_{self._device_id}_main_valve"
        self._attr_name = "Main valve"

    @property
    def is_on(self) -> bool:
        """Return True if main valve is on."""
        return self.coordinator.data.system_power == "on"

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on main valve."""
        await self.hass.async_add_executor_job(
            self.coordinator.api.set_dp, DP_SYSTEM_POWER, "on"
        )
        self.coordinator.async_set_updated_data(self.coordinator.api.device.snapshot())

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off main valve."""
        await self.hass.async_add_executor_job(
            self.coordinator.api.set_dp, DP_SYSTEM_POWER, "off"
        )
        self.coordinator.async_set_updated_data(self.coordinator.api.device.snapshot())


class InkbirdPowerSwitch(InkbirdEntity, SwitchEntity):
    """Switch for the power control."""

    _attr_icon = "mdi:power"

    def __init__(self, coordinator: InkbirdCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_{self._device_id}_power"
        self._attr_name = "Power"

    @property
    def is_on(self) -> bool:
        """Return True if power is on."""
        return self.coordinator.data.power_switch

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on."""
        await self.hass.async_add_executor_job(
            self.coordinator.api.set_dp, DP_POWER_SWITCH, True
        )
        self.coordinator.async_set_updated_data(self.coordinator.api.device.snapshot())

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off."""
        await self.hass.async_add_executor_job(
            self.coordinator.api.set_dp, DP_POWER_SWITCH, False
        )
        self.coordinator.async_set_updated_data(self.coordinator.api.device.snapshot())


class InkbirdRainSensorSwitch(InkbirdEntity, SwitchEntity):
    """Switch for the rain sensor."""

    _attr_icon = "mdi:weather-rainy"

    def __init__(self, coordinator: InkbirdCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_{self._device_id}_rain_sensor"
        self._attr_name = "Rain sensor"

    @property
    def is_on(self) -> bool:
        """Return True if rain sensor is enabled."""
        return self.coordinator.data.rain_sensor_enabled

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable rain sensor."""
        await self.hass.async_add_executor_job(
            self.coordinator.api.set_dp, DP_RAIN_SENSOR_ENABLED, True
        )
        self.coordinator.async_set_updated_data(self.coordinator.api.device.snapshot())

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable rain sensor."""
        await self.hass.async_add_executor_job(
            self.coordinator.api.set_dp, DP_RAIN_SENSOR_ENABLED, False
        )
        self.coordinator.async_set_updated_data(self.coordinator.api.device.snapshot())


class InkbirdSkipScheduleSwitch(InkbirdEntity, SwitchEntity):
    """Switch to skip/pause scheduled irrigation."""

    _attr_icon = "mdi:calendar-remove"

    def __init__(self, coordinator: InkbirdCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_{self._device_id}_skip_schedule"
        self._attr_name = "Skip schedule"

    @property
    def is_on(self) -> bool:
        """Return True if schedule is being skipped."""
        return self.coordinator.data.skip_schedule

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Skip schedule."""
        await self.hass.async_add_executor_job(
            self.coordinator.api.set_dp, DP_SKIP_SCHEDULE, True
        )
        self.coordinator.async_set_updated_data(self.coordinator.api.device.snapshot())

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Resume schedule."""
        await self.hass.async_add_executor_job(
            self.coordinator.api.set_dp, DP_SKIP_SCHEDULE, False
        )
        self.coordinator.async_set_updated_data(self.coordinator.api.device.snapshot())
