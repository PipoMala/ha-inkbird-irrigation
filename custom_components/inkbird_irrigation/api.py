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

# When running on the cloud fallback, how often to retry the local connection.
LOCAL_RETRY_INTERVAL = 300  # seconds (~5 minutes)


class InkbirdDevice:
    """Represents the state of an Inkbird IIC-600 irrigation controller."""

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
        self.active_zone_seen: bool = False
        self.queued_zone: int = 0

        # Per-zone state
        self.zone_active: dict[int, bool] = {z: False for z in range(1, NUM_ZONES + 1)}
        self.zone_countdown: dict[int, int] = {z: 0 for z in range(1, NUM_ZONES + 1)}
        self.zone_duration: dict[int, int] = {z: 0 for z in range(1, NUM_ZONES + 1)}
        self.zone_countdown_suppressed_until: dict[int, float] = {z: 0 for z in range(1, NUM_ZONES + 1)}

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
        new.active_zone_seen = self.active_zone_seen
        new.queued_zone = self.queued_zone
        new.zone_active = dict(self.zone_active)
        new.zone_countdown = dict(self.zone_countdown)
        new.zone_duration = dict(self.zone_duration)
        new.zone_countdown_suppressed_until = dict(self.zone_countdown_suppressed_until)
        return new

    def update_from_dps(self, dps: dict[str, Any]) -> None:
        """Update device state from Tuya data points."""
        for zone in range(1, NUM_ZONES + 1):
            dp_switch = str(DP_ZONE_SWITCH[zone])
            dp_countdown = str(DP_ZONE_COUNTDOWN[zone])
            dp_duration = str(DP_ZONE_DURATION[zone])

            if dp_switch in dps:
                self.zone_active[zone] = bool(dps[dp_switch])
            if dp_countdown in dps:
                countdown = int(dps[dp_countdown])
                if countdown == 0 or time.monotonic() >= self.zone_countdown_suppressed_until[zone]:
                    self.zone_countdown[zone] = countdown
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
            self.active_zone = int(dps[str(DP_ACTIVE_ZONE)])
            self.active_zone_seen = True
            for zone in range(1, NUM_ZONES + 1):
                zone_is_active = bool(self.active_zone & (1 << (zone - 1)))
                self.zone_active[zone] = zone_is_active
                if not zone_is_active:
                    self.zone_countdown[zone] = 0
        if str(DP_QUEUED_ZONE) in dps:
            self.queued_zone = int(dps[str(DP_QUEUED_ZONE)])


class InkbirdAPI:
    """Local Tuya API client for the Inkbird IIC-600.
    
    Uses a persistent socket connection to reduce session churn.
    Optionally falls back to Tuya Cloud API when local is unavailable.
    """

    def __init__(self, device_id: str, local_key: str, device_ip: str,
                 cloud_api_key: str = "", cloud_api_secret: str = "", cloud_api_region: str = "eu") -> None:
        self._device_id = device_id
        self._local_key = local_key
        self._device_ip = device_ip
        self._cloud_api_key = cloud_api_key
        self._cloud_api_secret = cloud_api_secret
        self._cloud_api_region = cloud_api_region
        self._tuya: tinytuya.Device | None = None
        self._cloud: tinytuya.Cloud | None = None
        self._connected = False
        self._fail_count = 0
        self._using_cloud = False
        self._command_lock = threading.Lock()
        self._last_local_retry = 0.0
        self.last_update_error = ""
        self.device = InkbirdDevice()

    @property
    def _has_cloud(self) -> bool:
        return bool(self._cloud_api_key and self._cloud_api_secret)

    @property
    def has_cloud(self) -> bool:
        """Whether cloud fallback credentials are configured."""
        return self._has_cloud

    @property
    def using_cloud(self) -> bool:
        """Whether the API is currently using the cloud connection."""
        return self._using_cloud

    @property
    def fail_count(self) -> int:
        """Number of consecutive local update failures."""
        return self._fail_count

    def validate_cloud(self) -> bool:
        """Validate cloud credentials by performing a cloud poll."""
        return self._cloud_update()

    def enable_cloud_fallback(self) -> bool:
        """Switch to the cloud connection. Returns True if the cloud poll succeeds."""
        if self._cloud_update():
            self._using_cloud = True
            return True
        return False

    def disconnect(self) -> None:
        """Close the persistent connection (call on unload)."""
        self._reset_connection()

    def _get_cloud(self) -> tinytuya.Cloud | None:
        """Get or create cloud client."""
        if not self._has_cloud:
            return None
        if not self._cloud:
            self._cloud = tinytuya.Cloud(
                apiRegion=self._cloud_api_region,
                apiKey=self._cloud_api_key,
                apiSecret=self._cloud_api_secret,
            )
        return self._cloud

    def _cloud_update(self) -> bool:
        """Poll device via cloud API (fallback)."""
        cloud = self._get_cloud()
        if not cloud:
            return False
        try:
            status = cloud.getstatus(self._device_id)
            if not status or not status.get("success") or not status.get("result"):
                return False
            # Map cloud status codes to DPs
            code_to_dp = {
                "switch_1": "1", "switch_2": "2", "switch_3": "3",
                "switch_4": "4", "switch_5": "5", "switch_6": "6",
                "countdown_1": "13", "countdown_2": "14", "countdown_3": "15",
                "countdown_4": "16", "countdown_5": "17", "countdown_6": "18",
                "use_time_1": "25", "use_time_2": "26", "use_time_3": "27",
                "use_time_4": "28", "use_time_5": "29", "use_time_6": "30",
                "water_control": "40", "control_skip": "43",
            }
            dps: dict[str, Any] = {}
            for item in status["result"]:
                code = item.get("code", "")
                dp = code_to_dp.get(code)
                if dp:
                    value = item["value"]
                    # Convert cloud enum to local format
                    if code == "water_control":
                        value = str(value)
                    dps[dp] = value
            if dps:
                self.device.online = True
                self.device.update_from_dps(dps)
                return True
            return False
        except Exception as exc:  # noqa: BLE001
            _LOGGER.debug("Cloud update failed: %s", exc)
            return False

    def _cloud_command(self, code: str, value: Any) -> bool:
        """Send command via cloud API."""
        cloud = self._get_cloud()
        if not cloud:
            return False
        try:
            commands = {"commands": [{"code": code, "value": value}]}
            result = cloud.sendcommand(self._device_id, commands)
            return result.get("success", False)
        except Exception as exc:  # noqa: BLE001
            _LOGGER.debug("Cloud command failed: %s", exc)
            return False

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
            self._fail_count = 0
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
        """Poll the device for current state. Falls back to cloud if local fails."""
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
        # If already using cloud (local was down at setup), skip local attempt
        if not self._using_cloud:
            # Try local first
            try:
                d = self._ensure_connection()
                if d:
                    # Force fresh DP read on persistent connection
                    d.updatedps()
                    time.sleep(0.5)
                    status = d.status()
                    if status and "dps" in status:
                        self.device.online = True
                        self.device.update_from_dps(status["dps"])
                        self._fail_count = 0
                        return True
                    self.last_update_error = f"Local status returned no dps: {status!r}"
                    self._fail_count += 1
                else:
                    self.last_update_error = "Local connection unavailable"
                    self._fail_count += 1
            except Exception as exc:  # noqa: BLE001
                self.last_update_error = f"Local update failed: {exc}"
                _LOGGER.debug("%s", self.last_update_error)
                self._fail_count += 1

            # Reset local connection after failures
            if self._fail_count >= 3:
                self._reset_connection()

            # Switch to cloud after 2 failures
            if self._has_cloud and self._fail_count >= 2:
                _LOGGER.warning("Local connection failed %d times, falling back to cloud API", self._fail_count)
                self._using_cloud = True
                self._last_local_retry = time.monotonic()

        # Use cloud (either as fallback or primary when local is down)
        if self._using_cloud and self._has_cloud:
            if self._cloud_update():
                # Periodically try to restore the local connection.
                now = time.monotonic()
                if now - self._last_local_retry >= LOCAL_RETRY_INTERVAL:
                    self._last_local_retry = now
                    self._reset_connection()
                    try:
                        d = self._ensure_connection()
                        if d:
                            status = d.status()
                            if status and "dps" in status:
                                _LOGGER.info("Local connection recovered, switching back from cloud")
                                self._using_cloud = False
                                self._fail_count = 0
                                self.device.update_from_dps(status["dps"])
                    except Exception:  # noqa: BLE001
                        pass
                return True
            self.last_update_error = self.last_update_error or "Cloud update failed"

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
        """Turn on a zone for the specified duration (1-180 minutes)."""
        if zone < 1 or zone > NUM_ZONES:
            return False
        self.device.zone_countdown_suppressed_until[zone] = 0
        self._wait_for_device()
        try:
            # If already in cloud mode, go straight to cloud
            if self._using_cloud and self._has_cloud:
                return self._cloud_turn_on(zone, duration_minutes)
            # Try local
            try:
                d = self._ensure_connection()
                if d:
                    # Start zone first, then set countdown just like the cloud API.
                    # Device only accepts countdown changes when zone is running
                    dp_countdown = DP_ZONE_COUNTDOWN[zone]
                    d.set_value(DP_ZONE_SWITCH[zone], True)
                    time.sleep(0.5)
                    d.set_value(dp_countdown, duration_minutes)
                    self.device.update_from_dps({
                        str(DP_ZONE_SWITCH[zone]): True,
                        str(dp_countdown): duration_minutes,
                        str(DP_ACTIVE_ZONE): 1 << (zone - 1),
                    })
                    _LOGGER.warning("Zone %d turned ON for %d minutes (local) - dp=%s", zone, duration_minutes, str(dp_countdown))
                    time.sleep(1)  # Wait for device to process before next command
                    return True
            except Exception as exc:  # noqa: BLE001
                _LOGGER.debug("Local turn_on_zone failed: %s", exc)
                self._reset_connection()
            # Fall back to cloud
            if self._has_cloud:
                return self._cloud_turn_on(zone, duration_minutes)
            return False
        finally:
            self._release_device()

    def _cloud_turn_on(self, zone: int, duration_minutes: int) -> bool:
        """Start a zone via cloud API."""
        cloud = self._get_cloud()
        if not cloud:
            return False
        try:
            # Order matters: switch ON first, then set countdown
            # Device only accepts countdown changes when zone is already running
            commands = {"commands": [
                {"code": f"switch_{zone}", "value": True},
                {"code": f"countdown_{zone}", "value": duration_minutes},
            ]}
            result = cloud.sendcommand(self._device_id, commands)
            if result.get("success", False):
                self.device.update_from_dps({
                    str(DP_ZONE_SWITCH[zone]): True,
                    str(DP_ZONE_COUNTDOWN[zone]): duration_minutes,
                    str(DP_ACTIVE_ZONE): 1 << (zone - 1),
                })
                _LOGGER.debug("Zone %d turned ON for %d minutes (cloud)", zone, duration_minutes)
                return True
            return False
        except Exception as exc:  # noqa: BLE001
            _LOGGER.debug("Cloud turn_on failed: %s", exc)
            return False

    def turn_off_zone(self, zone: int) -> bool:
        """Turn off a zone."""
        if zone < 1 or zone > NUM_ZONES:
            return False
        self._wait_for_device()
        try:
            # If already in cloud mode, go straight to cloud
            if self._using_cloud and self._has_cloud:
                code = f"switch_{zone}"
                if self._cloud_command(code, False):
                    self.device.zone_countdown_suppressed_until[zone] = time.monotonic() + 180
                    self.device.update_from_dps({
                        str(DP_ZONE_SWITCH[zone]): False,
                        str(DP_ZONE_COUNTDOWN[zone]): 0,
                    })
                    _LOGGER.debug("Zone %d turned OFF (cloud)", zone)
                    return True
                return False
            # Try local
            try:
                d = self._ensure_connection()
                if d:
                    d.set_value(DP_ZONE_SWITCH[zone], False)
                    self.device.zone_countdown_suppressed_until[zone] = time.monotonic() + 180
                    self.device.update_from_dps({
                        str(DP_ZONE_SWITCH[zone]): False,
                        str(DP_ZONE_COUNTDOWN[zone]): 0,
                    })
                    _LOGGER.debug("Zone %d turned OFF (local)", zone)
                    time.sleep(1)
                    return True
            except Exception as exc:  # noqa: BLE001
                _LOGGER.debug("Local turn_off_zone failed: %s", exc)
                self._reset_connection()
            # Fall back to cloud
            if self._has_cloud:
                code = f"switch_{zone}"
                if self._cloud_command(code, False):
                    self.device.zone_countdown_suppressed_until[zone] = time.monotonic() + 180
                    self.device.update_from_dps({
                        str(DP_ZONE_SWITCH[zone]): False,
                        str(DP_ZONE_COUNTDOWN[zone]): 0,
                    })
                    _LOGGER.debug("Zone %d turned OFF (cloud)", zone)
                    return True
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
