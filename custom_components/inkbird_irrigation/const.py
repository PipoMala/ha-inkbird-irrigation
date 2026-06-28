"""Constants for the Inkbird Irrigation integration."""

DOMAIN = "inkbird_irrigation"

# Tuya protocol
TUYA_VERSION = 3.4

# Number of zones on the IIC-600
NUM_ZONES = 6

# Data Point mapping for IIC-600-WIFI
# Zone switches (bool): True = valve open
DP_ZONE_SWITCH = {1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6}

# Zone countdown timers (int): seconds remaining
DP_ZONE_COUNTDOWN = {1: 13, 2: 14, 3: 15, 4: 16, 5: 17, 6: 18}

# Zone elapsed time counters (int): minutes elapsed since zone started
DP_ZONE_ELAPSED = {1: 25, 2: 26, 3: 27, 4: 28, 5: 29, 6: 30}

# Zone duration settings — not yet discovered which DP controls this
# The device appears to use a fixed 30-minute default
DP_ZONE_DURATION = {1: 25, 2: 26, 3: 27, 4: 28, 5: 29, 6: 30}  # placeholder

# System DPs
DP_SYSTEM_POWER = 40        # str: "on" / "off" — main valve control
DP_SKIP_SCHEDULE = 43       # bool — skip/pause scheduled irrigation
DP_MODE = 101               # str: "auto" / "manual"
DP_RAIN_SENSOR_ENABLED = 102  # bool — rain sensor main switch
DP_SEASONAL_ADJUST = 103    # int: seasonal adjustment percentage
DP_POWER_SWITCH = 107       # bool — power on/off
DP_AUTO_REMAINING = 109     # int: minutes remaining in auto irrigation
DP_ACTIVE_ZONE = 110        # int: bitmask of currently active zone
DP_QUEUED_ZONE = 111        # int: bitmask of queued zone

# Config entry keys
CONF_DEVICE_ID = "device_id"
CONF_LOCAL_KEY = "local_key"
CONF_DEVICE_IP = "device_ip"
CONF_DEVICE_NAME = "device_name"

# Optional cloud fallback credentials
CONF_CLOUD_API_KEY = "cloud_api_key"
CONF_CLOUD_API_SECRET = "cloud_api_secret"
CONF_CLOUD_API_REGION = "cloud_api_region"
