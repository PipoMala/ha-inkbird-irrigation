"""Inkbird IIC-600 WiFi local API client using Tuya protocol."""

from __future__ import annotations

import logging
from typing import Any

import tinytuya

from .const import (
    DP_MODE,
    DP_RAIN_DELAY_ACTIVE,
    DP_RAIN_DELAY_DURATION,
    DP_SCHEDULE_ENABLED,
    DP_SYSTEM_POWER,
    DP_ZONE_COUNTDOWN,
    DP_ZONE_DURATION,
    DP_ZONE_SWITCH,
    NUM_ZONES,
    TUYA_VERSION,
)

_LOGGER = logging.getLogger(__name__)


class InkbirdDevice:
    """Represents the state of an Inkbird IIC-600 irrigation controller."""

    def __init__(self) -> None:
        self.online: bool = False
        self.system_power: str = "on"
        self.mode: str = "auto"
        self.schedule_enabled: bool = True
        self.rain_delay_active: bool = False
        self.rain_delay_duration: int = 0

        # Per-zone state
        self.zone_active: dict[int, bool] = {z: False for z in range(1, NUM_ZONES + 1)}
        self.zone_countdown: dict[int, int] = {z: 0 for z in range(1, NUM_ZONES + 1)}
        self.zone_duration: dict[int, int] = {z: 0 for z in range(1, NUM_ZONES + 1)}

    def update_from_dps(self, dps: dict[str, Any]) -> None:
        """Update device state from Tuya data points."""
        for zone in range(1, NUM_ZONES + 1):
            dp_switch = str(DP_ZONE_SWITCH[zone])
            dp_countdown = str(DP_ZONE_COUNTDOWN[zone])
            dp_duration = str(DP_ZONE_DURATION[zone])

            if dp_switch in dps:
                self.zone_active[zone] = bool(dps[dp_switch])
            if dp_countdown in dps:
                self.zone_countdown[zone] = int(dps[dp_countdown])
            if dp_duration in dps:
                self.zone_duration[zone] = int(dps[dp_duration])

        if str(DP_SYSTEM_POWER) in dps:
            self.system_power = dps[str(DP_SYSTEM_POWER)]
        if str(DP_MODE) in dps:
            self.mode = dps[str(DP_MODE)]
        if str(DP_SCHEDULE_ENABLED) in dps:
            self.schedule_enabled = bool(dps[str(DP_SCHEDULE_ENABLED)])
        if str(DP_RAIN_DELAY_ACTIVE) in dps:
            self.rain_delay_active = bool(dps[str(DP_RAIN_DELAY_ACTIVE)])
        if str(DP_RAIN_DELAY_DURATION) in dps:
            self.rain_delay_duration = int(dps[str(DP_RAIN_DELAY_DURATION)])


class InkbirdAPI:
    """Local Tuya API client for the Inkbird IIC-600."""

    def __init__(self, device_id: str, local_key: str, device_ip: str) -> None:
        self._device_id = device_id
        self._local_key = local_key
        self._device_ip = device_ip
        self._tuya: tinytuya.Device | None = None
        self.device = InkbirdDevice()

    def connect(self) -> bool:
        """Initialize the Tuya device connection."""
        try:
            self._tuya = tinytuya.Device(self._device_id, self._device_ip, self._local_key)
            self._tuya.set_version(TUYA_VERSION)
            status = self._tuya.status()
            if status and "dps" in status:
                self.device.online = True
                self.device.update_from_dps(status["dps"])
                _LOGGER.debug("Connected to Inkbird IIC-600 at %s", self._device_ip)
                return True
            _LOGGER.error("No DPs returned from device at %s", self._device_ip)
            return False
        except Exception as exc:  # noqa: BLE001
            _LOGGER.error("Connection failed: %s", exc)
            return False

    def update(self) -> bool:
        """Poll the device for current state."""
        if not self._tuya:
            return False
        try:
            # Reconnect each poll to avoid stale socket
            self._tuya = tinytuya.Device(self._device_id, self._device_ip, self._local_key)
            self._tuya.set_version(TUYA_VERSION)
            status = self._tuya.status()
            if status and "dps" in status:
                self.device.online = True
                self.device.update_from_dps(status["dps"])
                return True
            self.device.online = False
            return False
        except Exception as exc:  # noqa: BLE001
            _LOGGER.debug("Update failed: %s", exc)
            self.device.online = False
            return False

    def turn_on_zone(self, zone: int, duration_minutes: int = 10) -> bool:
        """Turn on a zone for the specified duration."""
        if not self._tuya or zone < 1 or zone > NUM_ZONES:
            return False
        try:
            # Set duration first, then turn on
            dp_duration = DP_ZONE_DURATION[zone]
            dp_switch = DP_ZONE_SWITCH[zone]
            self._tuya.set_value(dp_duration, duration_minutes)
            self._tuya.set_value(dp_switch, True)
            _LOGGER.debug("Zone %d turned ON for %d minutes", zone, duration_minutes)
            return True
        except Exception as exc:  # noqa: BLE001
            _LOGGER.error("Failed to turn on zone %d: %s", zone, exc)
            return False

    def turn_off_zone(self, zone: int) -> bool:
        """Turn off a zone."""
        if not self._tuya or zone < 1 or zone > NUM_ZONES:
            return False
        try:
            dp_switch = DP_ZONE_SWITCH[zone]
            self._tuya.set_value(dp_switch, False)
            _LOGGER.debug("Zone %d turned OFF", zone)
            return True
        except Exception as exc:  # noqa: BLE001
            _LOGGER.error("Failed to turn off zone %d: %s", zone, exc)
            return False

    def set_zone_duration(self, zone: int, duration_minutes: int) -> bool:
        """Set the default duration for a zone."""
        if not self._tuya or zone < 1 or zone > NUM_ZONES:
            return False
        try:
            dp_duration = DP_ZONE_DURATION[zone]
            self._tuya.set_value(dp_duration, duration_minutes)
            return True
        except Exception as exc:  # noqa: BLE001
            _LOGGER.error("Failed to set duration for zone %d: %s", zone, exc)
            return False
