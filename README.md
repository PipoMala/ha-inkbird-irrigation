# Inkbird Irrigation - Home Assistant Integration

A custom Home Assistant integration for the **Inkbird IIC-600-WIFI** smart irrigation controller. Full local control — no cloud dependency.

[![GitHub Release](https://img.shields.io/github/release/ac-uy/ha-inkbird-irrigation.svg?style=flat-square)](https://github.com/ac-uy/ha-inkbird-irrigation/releases)
[![License](https://img.shields.io/badge/license-MIT-blue.svg?style=flat-square)](https://github.com/ac-uy/ha-inkbird-irrigation/blob/master/LICENSE)
[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg?style=flat-square)](https://hacs.xyz/)

## Features

- 💧 **6 zone control** — turn valves on/off individually
- ⏱️ **Duration settings** — set watering time per zone (1-240 minutes)
- 📊 **Countdown timers** — see remaining time for each active zone
- 🏠 **100% Local** — communicates directly with the device on your LAN (no cloud)
- 🔒 **No internet required** — works even if your internet is down
- 🌧️ **Rain delay status** — see if rain delay is active

## Supported Devices

- **Inkbird IIC-600-WIFI** (6-zone sprinkler controller)
- **Inkbird IIC-800-WIFI** (8-zone, untested but likely compatible)

## Prerequisites

Before installing this integration, you need your device's **Local Key** from the Tuya IoT Platform. This is a one-time setup.

### Getting Your Device Credentials

1. **Create a Tuya IoT account** at https://iot.tuya.com
2. **Create a Cloud Project** → select "Smart Home" and your data center region
3. **Pair your IIC-600 with the Tuya Smart app** (not the Inkbird app):
   - Remove the device from the Inkbird app
   - Download the **Tuya Smart** app
   - Add the IIC-600 as a new device in Tuya Smart
4. **Link your Tuya Smart account** to the IoT Platform:
   - Go to Devices → Link Tuya App Account → scan QR with Tuya Smart app
5. **Get the Local Key**:
   - Go to API Explorer → Device Management → Get Device Information
   - Enter your Device ID (find it via the Tuya Smart app or network scan)
   - The response contains the `local_key`
6. **Find the device IP** on your router (look for the IIC-600 or run `python -m tinytuya scan`)

### Device Credentials You Need

| Field | Where to find it |
|-------|-----------------|
| Device ID | Tuya IoT Platform or `python -m tinytuya scan` |
| Local Key | Tuya IoT Platform API Explorer |
| Device IP | Your router's connected devices list |

## Installation

### Via HACS (Recommended)

1. Open **HACS** in Home Assistant
2. Go to **Integrations** → **⋮ (menu)** → **Custom repositories**
3. Add repository: `https://github.com/ac-uy/ha-inkbird-irrigation`
4. Select category: **Integration**
5. Find **Inkbird Irrigation** and click **Install**
6. Restart Home Assistant

### Manual Installation

1. Copy `custom_components/inkbird_irrigation` to your HA `config/custom_components/` directory
2. Restart Home Assistant

## Setup

1. Go to **Settings** → **Devices & Services** → **Add Integration**
2. Search for **"Inkbird"**
3. Enter your device credentials (Device ID, Local Key, IP address)
4. Click **Submit**

## Entities Created

| Entity | Type | Description |
|--------|------|-------------|
| `switch.inkbird_zone_1` - `zone_6` | Switch | Zone valve on/off |
| `sensor.inkbird_zone_1_time_remaining` - `zone_6` | Sensor | Countdown (seconds) |
| `number.inkbird_zone_1_duration` - `zone_6` | Number | Duration setting (minutes) |
| `sensor.inkbird_mode` | Sensor | Operating mode (auto/manual) |

## Usage

### Turn on a zone for 15 minutes

```yaml
service: switch.turn_on
target:
  entity_id: switch.inkbird_iic_600_zone_1
```

Set the duration first via the number entity, then turn on the switch.

### Automation: Water front garden every morning

```yaml
automation:
  - alias: "Morning watering"
    trigger:
      platform: time
      at: "07:00:00"
    action:
      - service: number.set_value
        target:
          entity_id: number.inkbird_iic_600_zone_1_duration
        data:
          value: 20
      - service: switch.turn_on
        target:
          entity_id: switch.inkbird_iic_600_zone_1
```

## Technical Details

- **Protocol**: Tuya local protocol v3.4
- **Communication**: Direct LAN (UDP/TCP on device IP)
- **Polling interval**: 15 seconds
- **No cloud dependency**: Works entirely on your local network

## Troubleshooting

### Cannot connect to device

- Verify the device IP hasn't changed (set a static IP in your router)
- Check the Local Key is current (it can change if you re-pair the device)
- Ensure the device is on the same network as Home Assistant

### Local Key changed

If you re-pair the device with any app, the Local Key changes. Get the new one from Tuya IoT Platform.

### Device not found on network scan

- Make sure the IIC-600 is powered on and connected to WiFi
- Run `python -m tinytuya scan` from a machine on the same network

## License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

The MIT License allows you to:
- ✅ Use this software for any purpose
- ✅ Copy, modify, and distribute it
- ✅ Include it in proprietary applications

The only requirement is to include the license and copyright notice.

## Disclaimer

This is an unofficial integration. Inkbird is not affiliated with this project. Use at your own risk.

## Credits

- Built for Home Assistant
- Uses [tinytuya](https://github.com/jasonacox/tinytuya) for local Tuya protocol communication
- First integration to provide local control of Inkbird irrigation controllers

---

**Questions or Issues?** [Open an issue on GitHub](https://github.com/ac-uy/ha-inkbird-irrigation/issues)
