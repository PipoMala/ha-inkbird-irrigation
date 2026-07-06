"""Constants for the Inkbird Irrigation integration."""

DOMAIN = "inkbird_irrigation"

# Tuya protocol
TUYA_VERSION = 3.3

# Number of zones on the IIC-600
NUM_ZONES = 6

# Data Point mapping for IIC-600-WIFI
# Zone switches (bool): True = valve open
DP_ZONE_SWITCH = {1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6}

# Zone countdown timers (int) — Tuya "countdown_N" / 灌溉时间: the watering
# duration/remaining time in MINUTES (0-180). Writing this (with the zone
# switch on) is the device-native way to run a zone for N minutes.
DP_ZONE_COUNTDOWN = {1: 13, 2: 14, 3: 15, 4: 16, 5: 17, 6: 18}

# Zone elapsed time (int) — Tuya "use_time_N" / 单次使用时间: minutes elapsed in
# the current run (0-360).
DP_ZONE_ELAPSED = {1: 25, 2: 26, 3: 27, 4: 28, 5: 29, 6: 30}

# There is no separate "zone duration" data point: duration is set via the
# countdown DP above. This alias points at the elapsed-time DPs and is only used
# to surface the "time elapsed" sensor.
DP_ZONE_DURATION = {1: 25, 2: 26, 3: 27, 4: 28, 5: 29, 6: 30}

# System DPs (codes confirmed against a real IIC-600-WIFI device)
DP_SYSTEM_POWER = 40        # enum "on"/"off" — water_control (master valve)
DP_SKIP_SCHEDULE = 43       # bool — control_skip (skip/pause scheduled irrigation)
DP_MODE = 101               # enum "auto"/"manual" — operation_mode
DP_RAIN_SENSOR_ENABLED = 102  # bool — RainSen_TotalONOFF (rain sensor main switch)
DP_SEASONAL_ADJUST = 103    # int — SeaAdjValue (seasonal adjustment percentage)
DP_POWER_SWITCH = 107       # bool — main_switch (device power on/off)
DP_AUTO_REMAINING = 109     # int — auto_remaining_time (minutes remaining in auto)
DP_ACTIVE_ZONE = 110        # int — zonerun_state (running zone; encoding unreliable, not used for state)
DP_QUEUED_ZONE = 111        # int — pendingzone_state (queued zone)

# Config entry keys
CONF_DEVICE_ID = "device_id"
CONF_LOCAL_KEY = "local_key"
CONF_DEVICE_IP = "device_ip"
CONF_DEVICE_NAME = "device_name"
