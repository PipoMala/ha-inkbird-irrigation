"""Inkbird IIC-600 WiFi local API client using Tuya protocol."""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

import tinytuya

from .const import (
    DP_ACTIVE_ZONE,
    DP_AUTO_REMAINING,
    DP_MODE,
    DP_POWER_SWITCH,
    DP_QUEUED_ZONE,
    DP_RAIN_SENSOR_ENABLED,
    DP_SEASONAL_ADJUST,
    DP_SKIP_SCHEDULE,
    DP_SYSTEM_POWER,
    DP_ZONE_COUNTDOWN,
    DP_ZONE_DURATION,
    DP_ZONE_SWITCH,
    NUM_ZONES,
    TUYA_VERSION,
)

_LOGGER = logging.getLogger(__name__)

# After a zone is commanded ON, trust the optimistic on-state for this long so a
# poll that runs before the device has registered the start cannot momentarily
# reset the zone to "off". Cleared as soon as the device confirms the zone.
ZONE_TURN_ON_GRACE = 45  # seconds (~3 poll intervals)


class InkbirdDevice:
    """State of an Inkbird IIC-600 irrigation controller.

    Zone on/off state has a single source of truth: the per-zone switch DPs
    (1-6). The device countdown DPs (13-18) are surfaced only as a
    remaining-time display. Home Assistant owns all timing.
    """

    def __init__(self) -> None:
        self.online: bool = False
        self.system_power: str = "on"
        self.mode: str = "auto"
        self.power_switch: bool = True
        self.skip_schedule: bool = False
        self.rain_sensor_enabled: bool = True
        self.seasonal_adjust: int = 0
        self.auto_remaining: int = 0
        self.active_zone: int = 0
        self.queued_zone: int = 0

        # Per-zone state
        self.zone_active: dict[int, bool] = {z: False for z in range(1, NUM_ZONES + 1)}
        self.zone_countdown: dict[int, int] = {z: 0 for z in range(1, NUM_ZONES + 1)}
        self.zone_duration: dict[int, int] = {z: 0 for z in range(1, NUM_ZONES + 1)}
        self.zone_turn_on_grace_until: dict[int, float] = {z: 0 for z in range(1, NUM_ZONES + 1)}

    def snapshot(self) -> "InkbirdDevice":
        """Return a copy with independent dicts for a consistent, thread-safe read.

        Each ``dict(...)`` copy is atomic under the GIL, so the returned object is
        safe to read from the event loop while the executor mutates the live one.
        """
        new = InkbirdDevice()
        new.online = self.online
        new.system_power = self.system_power
        new.mode = self.mode
        new.power_switch = self.power_switch
        new.skip_schedule = self.skip_schedule
        new.rain_sensor_enabled = self.rain_sensor_enabled
        new.seasonal_adjust = self.seasonal_adjust
        new.auto_remaining = self.auto_remaining
        new.active_zone = self.active_zone
        new.queued_zone = self.queued_zone
        new.zone_active = dict(self.zone_active)
        new.zone_countdown = dict(self.zone_countdown)
        new.zone_duration = dict(self.zone_duration)
        new.zone_turn_on_grace_until = dict(self.zone_turn_on_grace_until)
        return new

    def update_from_dps(self, dps: dict[str, Any]) -> None:
        """Update device state from Tuya data points."""
        now = time.monotonic()
        for zone in range(1, NUM_ZONES + 1):
            dp_switch = str(DP_ZONE_SWITCH[zone])
            dp_countdown = str(DP_ZONE_COUNTDOWN[zone])
            dp_duration = str(DP_ZONE_DURATION[zone])
            in_turn_on_grace = now < self.zone_turn_on_grace_until[zone]

            if dp_switch in dps:
                new_switch = bool(dps[dp_switch])
                if new_switch:
                    # Device confirmed the zone is running: accept and end grace.
                    self.zone_active[zone] = True
                    self.zone_turn_on_grace_until[zone] = 0
                elif not in_turn_on_grace:
                    self.zone_active[zone] = False
                # else: keep the optimistic True during the turn-on grace window
            if dp_countdown in dps:
                self.zone_countdown[zone] = int(dps[dp_countdown])
            if dp_duration in dps:
                self.zone_duration[zone] = int(dps[dp_duration])

        if str(DP_SYSTEM_POWER) in dps:
            self.system_power = dps[str(DP_SYSTEM_POWER)]
        if str(DP_MODE) in dps:
            self.mode = dps[str(DP_MODE)]
        if str(DP_POWER_SWITCH) in dps:
            self.power_switch = bool(dps[str(DP_POWER_SWITCH)])
        if str(DP_SKIP_SCHEDULE) in dps:
            self.skip_schedule = bool(dps[str(DP_SKIP_SCHEDULE)])
        if str(DP_RAIN_SENSOR_ENABLED) in dps:
            self.rain_sensor_enabled = bool(dps[str(DP_RAIN_SENSOR_ENABLED)])
        if str(DP_SEASONAL_ADJUST) in dps:
            self.seasonal_adjust = int(dps[str(DP_SEASONAL_ADJUST)])
        if str(DP_AUTO_REMAINING) in dps:
            self.auto_remaining = int(dps[str(DP_AUTO_REMAINING)])
        if str(DP_ACTIVE_ZONE) in dps:
            # DP 110 ("zonerun_state") reports the running zone, but its encoding
            # (index vs bitmask) is not reliable across firmware revisions, so it
            # is stored for reference only and is NOT used to derive per-zone
            # on/off state. Zone state comes from the unambiguous per-zone switch
            # DPs (1-6) handled above.
            self.active_zone = int(dps[str(DP_ACTIVE_ZONE)])
        if str(DP_QUEUED_ZONE) in dps:
            self.queued_zone = int(dps[str(DP_QUEUED_ZONE)])


class InkbirdAPI:
    """Local-only Tuya API client for the Inkbird IIC-600 (persistent socket)."""

    def __init__(self, device_id: str, local_key: str, device_ip: str) -> None:
        self._device_id = device_id
        self._local_key = local_key
        self._device_ip = device_ip
        self._tuya: tinytuya.Device | None = None
        self._connected = False
        self._command_lock = threading.Lock()
        self.last_update_error = ""
        self.device = InkbirdDevice()

    def disconnect(self) -> None:
        """Close the persistent connection (call on unload)."""
        self._reset_connection()

    def _ensure_connection(self) -> tinytuya.Device | None:
        """Get or create a persistent connection."""
        if self._tuya and self._connected:
            return self._tuya
        try:
            self._tuya = tinytuya.Device(self._device_id, self._device_ip, self._local_key)
            self._tuya.set_version(TUYA_VERSION)
            self._tuya.set_socketPersistent(True)
            self._tuya.set_socketTimeout(5)
            self._connected = True
            _LOGGER.debug("Persistent connection established to %s", self._device_ip)
            return self._tuya
        except Exception as exc:  # noqa: BLE001
            _LOGGER.debug("Connection setup failed: %s", exc)
            self._connected = False
            return None

    def _reset_connection(self) -> None:
        """Close and reset the connection."""
        if self._tuya:
            try:
                self._tuya.close()
            except Exception:  # noqa: BLE001
                pass
        self._tuya = None
        self._connected = False

    def connect(self) -> bool:
        """Initialize the Tuya device connection."""
        try:
            d = self._ensure_connection()
            if not d:
                return False
            status = d.status()
            if status and "dps" in status:
                self.device.online = True
                self.device.update_from_dps(status["dps"])
                _LOGGER.debug("Connected to Inkbird IIC-600 at %s", self._device_ip)
                return True
            _LOGGER.error("No DPs returned from device at %s", self._device_ip)
            self._reset_connection()
            return False
        except Exception as exc:  # noqa: BLE001
            _LOGGER.error("Connection failed: %s", exc)
            self._reset_connection()
            return False

    def update(self) -> bool:
        """Poll the device for current state."""
        # Skip this poll if a command is in progress; the command refreshes state.
        if not self._command_lock.acquire(blocking=False):
            return True
        try:
            return self._poll()
        finally:
            self._command_lock.release()

    def _poll(self) -> bool:
        """Perform the actual polling. Caller must hold the command lock."""
        self.last_update_error = ""
        try:
            d = self._ensure_connection()
            if not d:
                self.last_update_error = "Local connection unavailable"
                self.device.online = False
                return False
            # Force a fresh DP read on the persistent connection.
            d.updatedps()
            time.sleep(0.5)
            status = d.status()
            if status and "dps" in status:
                self.device.online = True
                self.device.update_from_dps(status["dps"])
                return True
            self.last_update_error = f"Local status returned no dps: {status!r}"
        except Exception as exc:  # noqa: BLE001
            self.last_update_error = f"Local update failed: {exc}"
            _LOGGER.debug("%s", self.last_update_error)
            self._reset_connection()
        self.device.online = False
        return False

    def _wait_for_device(self) -> None:
        """Acquire the command lock and wait for the device to be ready."""
        self._command_lock.acquire()
        time.sleep(1)  # Minimum gap between commands

    def _release_device(self) -> None:
        """Release the command lock after the current command finishes."""
        self._command_lock.release()

    def turn_on_zone(self, zone: int, duration_minutes: int = 30) -> bool:
        """Open a zone valve.

        Home Assistant owns the timing and turns the zone off after the
        configured duration; the device countdown is set only as a best-effort
        safety stop and as the remaining-time display.
        """
        if zone < 1 or zone > NUM_ZONES:
            return False
        self._wait_for_device()
        try:
            d = self._ensure_connection()
            if not d:
                return False
            # Start the zone, then set its countdown (the device only accepts a
            # countdown change once the zone is running).
            dp_countdown = DP_ZONE_COUNTDOWN[zone]
            d.set_value(DP_ZONE_SWITCH[zone], True)
            time.sleep(0.5)
            d.set_value(dp_countdown, duration_minutes)
            self.device.update_from_dps({
                str(DP_ZONE_SWITCH[zone]): True,
                str(dp_countdown): duration_minutes,
            })
            self.device.zone_turn_on_grace_until[zone] = time.monotonic() + ZONE_TURN_ON_GRACE
            _LOGGER.debug("Zone %d turned ON for %d minutes", zone, duration_minutes)
            time.sleep(1)  # let the device process before the next command
            return True
        except Exception as exc:  # noqa: BLE001
            _LOGGER.debug("turn_on_zone failed: %s", exc)
            self._reset_connection()
            return False
        finally:
            self._release_device()

    def turn_off_zone(self, zone: int) -> bool:
        """Close a zone valve."""
        if zone < 1 or zone > NUM_ZONES:
            return False
        # Cancel any pending turn-on grace so this explicit stop is honoured.
        self.device.zone_turn_on_grace_until[zone] = 0
        self._wait_for_device()
        try:
            d = self._ensure_connection()
            if not d:
                return False
            d.set_value(DP_ZONE_SWITCH[zone], False)
            self.device.update_from_dps({
                str(DP_ZONE_SWITCH[zone]): False,
                str(DP_ZONE_COUNTDOWN[zone]): 0,
            })
            _LOGGER.debug("Zone %d turned OFF", zone)
            time.sleep(1)
            return True
        except Exception as exc:  # noqa: BLE001
            _LOGGER.debug("turn_off_zone failed: %s", exc)
            self._reset_connection()
            return False
        finally:
            self._release_device()

    def set_dp(self, dp: int, value: Any) -> bool:
        """Set a single data point value."""
        self._wait_for_device()
        try:
            d = self._ensure_connection()
            if not d:
                return False
            d.set_value(dp, value)
            self.device.update_from_dps({str(dp): value})
            _LOGGER.debug("Set DP %d = %r", dp, value)
            return True
        except Exception as exc:  # noqa: BLE001
            _LOGGER.error("Failed to set DP %d: %s", dp, exc)
            self._reset_connection()
            return False
        finally:
            self._release_device()
