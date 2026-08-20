# SmegConnect — Unofficial Home Assistant Integration

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/aleks-mariusz/smegconnect-homeassistant)

An unofficial Home Assistant integration for Smeg smart appliances — ovens, blast chillers, dishwashers, and wine coolers — connected via the SmegConnect cloud platform.

> **Status:** Pre-release / beta. Tested on SOP6606WS2PNR (oven) and SBC4604WNR1 (blast chiller). Reverse-engineered from the SmegConnect and SmegConnect Plus Android apps.

---

## What is SmegConnect?

SmegConnect is Smeg's cloud platform for controlling smart appliances remotely via a mobile app. Appliances connect to the Smeg cloud (hosted on AWS) and receive commands and push real-time state updates over MQTT. This integration connects to the same cloud API, giving you control and monitoring from Home Assistant without any local network access required.

**Architecture:** `HA → Smeg Cloud REST API + STOMP/WebSocket → AWS IoT MQTT → Appliance`

The appliance connects outbound to the Smeg cloud; there is no supported local control API after provisioning.

---

## SmegConnect vs SmegConnect Plus

Smeg publishes two separate apps that share the same cloud infrastructure (same AWS backend, same account, same credentials) but target different appliance categories:

| | SmegConnect | SmegConnect Plus |
|---|---|---|
| **Supported devices** | Ovens, dishwashers, wine coolers | Blast chillers (+ dishwashers being migrated) |
| **API version used** | v1 (`/api/v1/…`) | v2 (`/api/v2/…`) for device listing and auth |
| **Auth endpoint** | `POST /api/v1/auth/token` | `POST /api/v2/auth/login` |
| **Device listing** | `GET /api/v1/devices` | `POST /api/v2/devices` (with parameter list) |
| **Command endpoint** | `POST /api/v1/devices/{code}/commands` | Same — v2 commands use the identical format |
| **State fields** | Named fields (`doorState`, `childlock`, `appl`) | Bit arrays (`applState1/2_*`) for blast chiller — decoded by integration using `BlastChillerStatusTransformer` from Plus APK |

**Both apps use the same Smeg cloud.** A device enrolled via either app can be commanded via either API version. You do not need two accounts.

**This integration uses v1 endpoints uniformly** for all device types. The v1 `GET /api/v1/devices` listing returns every enrolled appliance regardless of which app was used to provision it. Commands sent via v1 are confirmed working for both ovens (SmegConnect) and blast chillers (SmegConnect Plus).

**v2 device listing is scoped by app category.** `POST /api/v2/devices` only returns devices enrolled via SmegConnect Plus — ovens enrolled via SmegConnect do not appear. For this reason, the integration uses v1 as the authoritative device list source.

> **Blast chiller bit arrays:** The blast chiller firmware encodes several boolean states as positional bits in generic `applState2_*` fields. The integration decodes these using the bit map extracted from `BlastChillerStatusTransformer.java` in the SmegConnect Plus APK — child lock and appliance on/off state are fully supported. Door state (`doorState`) is **not available** for the SBC4604WNR1: no door bit exists in the firmware's state register (confirmed from Plus APK source).

---

## Prerequisites

1. **A SmegConnect account** — create one in the SmegConnect or SmegConnect Plus app.
2. **Enrolled appliances** — each appliance must be provisioned into your account via the app.

> **TODO:** Automated account creation and appliance enrollment scripts are planned — see `smeg-run.sh` in the companion tools directory for the provisioning flow.

---

## Installation

### Via HACS (recommended)

1. In Home Assistant: **HACS → ⋮ → Custom repositories**
2. Add URL: `https://github.com/aleks-mariusz/smegconnect-homeassistant` — Category: **Integration**
3. Search for "SmegConnect" in HACS and install
4. Restart Home Assistant

### Manual

Copy `custom_components/smeg/` to your HA `config/custom_components/smeg/` directory and restart.

---

## Configuration

1. **Settings → Devices & Services → Add Integration → SmegConnect**
2. Enter your SmegConnect account email and password
3. The integration logs in, discovers all enrolled appliances, and creates a device for each one

Devices are named using the full commercial product code, e.g.:
- `Smeg Pyrolytic SteamOne Oven / 60 cm / Dolce Stil Novo`
- `Smeg Multisense Blast Chiller / 45 cm / Dolce Stil Novo`

---

## Entities

### Oven

| Platform | Entity | Description |
|---|---|---|
| `climate` | Oven | On/off (HEAT/OFF mode) + target temperature. Temperature setting does **not** turn the oven on — use the mode toggle separately. |
| `sensor` | Cavity Temperature | Current oven cavity temperature (°C) |
| `sensor` | Target Temperature | Set-point temperature |
| `sensor` | Cooking Elapsed / Remaining | Time into / left in the current cooking cycle |
| `sensor` | Cooking Phase | standby / preheating / cooking / cooling |
| `binary_sensor` | Door | Open/Closed |
| `binary_sensor` | Meat Probe Connected | Whether the meat probe is physically plugged in |
| `sensor` | Meat Probe Temperature | Probe temperature (only when connected) |
| `switch` | Light | Oven cavity light |
| `switch` | Keep Warm | Keep-warm mode after cooking |
| `number` | Timer 1/2/3 | Countdown timers (seconds) |
| `number` | Water Hardness | Limescale setting for steam boiler (1–5) |
| **Configuration** | | |
| `select` | Temperature Format | °C / °F |
| `select` | Clock Format | 24h / 12h |
| `select` | Weight Format | kg / oz |
| `select` | Clock Font | Normal / Digital (clock display style) |
| `switch` | Eco Light | Energy-saving cavity light mode |
| `switch` | Eco Logic | Energy optimisation mode |
| `switch` | Sound | Audible alerts |
| `switch` | Child Lock | Panel lockout |
| `number` | Display Brightness | Screen brightness (0–100) |
| **Diagnostic** | | |
| `binary_sensor` | Error Active | True when an error code is present |
| `sensor` | Error Code / Error Description | Fault information |
| `sensor` | CB Firmware, Main Software, etc. | See firmware version table below |

### Blast Chiller

| Platform | Entity | Description |
|---|---|---|
| `sensor` | Cavity Temperature | Current cavity temperature (°C) |
| `sensor` | Step 1/2/3 Target Temperature | Chilling program step targets |
| `sensor` | Meat Probe Temperature | When probe connected |
| `binary_sensor` | Meat Probe Connected | Probe insertion status |
| `binary_sensor` | Child Lock Active | Child lock state (decoded from `applState2_001`) |
| `binary_sensor` | Cloud Connected | Cloud connectivity status |
| `binary_sensor` | Remote Control Enabled | Whether remote commands are accepted |
| `number` | Step 1/2/3 Target Temperature | Set chilling step temperatures |
| `number` | Timer 1/2 | Countdown timers |
| `number` | Display Brightness | Screen brightness |
| `select` | Temperature Format, Clock Format, Weight Format, Clock Font | Display settings |
| `switch` | Sound, Child Lock | Settings |

> **Note:** Door state is not available for the blast chiller. The SBC4604WNR1 firmware does not expose door open/closed state remotely — confirmed by decompiling `BlastChillerStatusTransformer.java` from the SmegConnect Plus APK: no door bit exists in the firmware's `applState2_*` register.

---

## Firmware Version Diagnostics

All firmware sensors appear under the **Diagnostic** section of each device. Labels in parentheses are what you see on the physical appliance's diagnostic screen.

| HA Sensor | Screen Label | Description |
|---|---|---|
| CB Firmware (SOFTW CB) | `SOFTW CB` | Connectivity Board firmware version |
| Main Software (SOFTW) | `SOFTW` | Power board application software |
| Power Board Kernel (KERNEL POWER) | `KERNEL POWER` | Power board OS kernel |
| Parameter Software (PARSW) | `PARSW` | Machine calibration & settings data |
| Display Firmware (FIRMW TFT) | `FIRMW TFT` | TFT display board firmware |
| Display Kernel (KERNEL TFT) | `KERNEL TFT` | TFT display board kernel |
| Display Schema (SCHTX) | `SCHTX` | Display structure/schema software |
| Meat Probe Firmware (MASTER PROBE) | `MASTER PROBE` | Meat probe module firmware |
| Meat Probe Kernel (KERNEL PROBE) | `KERNEL PROBE` | Meat probe module kernel |
| Category ID (APPL_CAT_ID) | `APPL_CAT_ID` | Appliance type ID (4=Oven, 47=Blast Chiller) |
| Appliance Category | — | Human-readable decode of Category ID |
| Model ID (APPL_MODEL_ID) | `APPL_MODEL_ID` | Internal model number |
| Data Model ID (APPL_DATAMODEL_ID) | `APPL_DATAMODEL_ID` | Firmware data model variant |

---

## Remote Control — Important

Many operational commands (oven power, light, cooking temperature) require **Remote Control** to be enabled on the appliance's physical display. This is separate from the app and must be set on the device itself.

**To enable:** On the oven display, navigate to the connectivity/remote settings menu (varies by model — typically a Wi-Fi or phone icon, long-press or menu button) and enable "Remote Control" or "SmegConnect". You will see the `Remote Control Enabled` diagnostic sensor in HA flip to **On**.

**Commands that require Remote Control ON:**
- Oven power on/off
- Oven light
- Keep Warm

**Commands that work regardless of Remote Control state:**
- All settings (temperature format, clock font, brightness, sound, eco modes, timers, etc.)

**Opening the door disables Remote Control.** When you open the oven or blast chiller door, the `remoteControl` field is set to OFF by the firmware as a safety measure. You must close the door and re-enable Remote Control on the display before sending operational commands again.

**Child lock blocks Remote Control.** When Child Lock is physically active on the appliance display, the firmware rejects all remote operational commands (the API returns 202 Accepted, but the appliance silently ignores the command). To restore remote control: disable child lock on the physical display first.

---

## Real-time Updates

The integration uses **STOMP over WebSocket** (`wss://ws.prod-platform.smegconnect.com/register/websocket`) for real-time state pushes. When connected, entity states update within 1–5 seconds of a physical change. If the WebSocket disconnects, the integration automatically falls back to **10-second REST polling** and attempts to reconnect (with exponential backoff: 30s → 60s → 120s → max 5 minutes).

---

## Supported Models

All 80 SmegConnect/SmegConnect Plus supported models are in the integration's catalog. Device names are automatically derived from the internal model number → commercial code mapping extracted from the SmegConnect Plus app.

| Type | Models |
|---|---|
| Ovens | SOP6606WS2PNR, SO6606WAPNR, SO4606WAPNR, SO4606WM2PNR, SO4606WS4PNR, SO6606WS4PNR, and 40+ more |
| Blast Chillers | SBC4604WNR1, SBC4304WX, SBC4104WG/WB3 |
| Dishwashers | STL324BQLLW, STL7324AQLLW, STL7324BLW |
| Wine Coolers | CVI638RWN3/LWN3, CVI621RWNR3/LWNR3, and 18+ more |

---

## Limitations & Known Issues

- **Local control not available** — the CB firmware shuts down its local HTTPS API (port 13335) after provisioning. All control is via the Smeg cloud.
- **Blast chiller door state** — the SBC4604WNR1 firmware does not expose door open/closed state. Child lock and appliance on/off are decoded and available as sensors (v0.1.6+). Door state is a confirmed firmware limitation.
- **Oven 2 (4G AUX variant)** — devices with a CB v0.0.0 or 4G auxiliary module may not provision via the standard flow. Contact Smeg support.
- **PARSW number** (e.g. PARSW0436) — this is static ADF metadata not returned by the live API; only the PARSW version number is available.
- **Firmware upgrade status** — no sensor for pending OTA updates yet; planned for a future release.

---

## License

Unofficial integration. Not affiliated with or endorsed by Smeg S.p.A.
