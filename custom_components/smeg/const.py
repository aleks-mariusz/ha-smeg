"""Constants for the SmegConnect integration."""
from __future__ import annotations

DOMAIN = "smeg"

API_BASE = "https://smegcons.prod-platform.smegconnect.com"
WS_BASE = "wss://ws.prod-platform.smegconnect.com/register"
TENANT = "smegcons"

# Config entry keys
CONF_ACCESS_TOKEN = "access_token"
CONF_REFRESH_TOKEN = "refresh_token"
CONF_IOT_USER_CODE = "iot_user_code"

# Device type IDs (from GET /api/v1/devices deviceTypeId field)
DEVICE_TYPE_OVEN = 7
DEVICE_TYPE_BLAST_CHILLER = 12
DEVICE_TYPE_DISHWASHER = 2
DEVICE_TYPE_WINE_CHILLER = 4

DEVICE_TYPE_NAMES = {
    DEVICE_TYPE_OVEN: "Oven",
    DEVICE_TYPE_BLAST_CHILLER: "Blast Chiller",
    DEVICE_TYPE_DISHWASHER: "Dishwasher",
    DEVICE_TYPE_WINE_CHILLER: "Wine Chiller",
}

# Command version per device type (confirmed from Charles captures)
DEVICE_TYPE_COMMAND_VERSION: dict[int, str] = {
    DEVICE_TYPE_OVEN: "4.0",
    DEVICE_TYPE_BLAST_CHILLER: "4.0",
    DEVICE_TYPE_DISHWASHER: "3.0",
    DEVICE_TYPE_WINE_CHILLER: "3.0",
}

# Oven command codes (confirmed from Charles captures unless noted)
CMD_POWER_ON = "Sys_OpSetPowerOnFeature"   # also used for set-temperature
CMD_POWER_OFF = "Sys_OpSetPowerOffFeature"
CMD_LIGHT = "lightFeature"                 # confirmed
CMD_KEEP_WARM = "keepWarmFeature"
CMD_ECO_LIGHT = "ecoLightFeature"
CMD_ECO_LOGIC = "ecoLogicFeature"
CMD_CHILDLOCK = "childlockFeature"
CMD_TIMER1 = "timer1Feature"
CMD_TIMER2 = "timer2Feature"
CMD_TIMER3 = "timer3Feature"
CMD_DISP_BRIGHTNESS = "dispBrightnessFeature"

# Blast chiller command codes
CMD_SEQ_START = "currSeqStartCmd"
CMD_SEQ_STOP = "currSeqStopCmd"
CMD_STEP1_TEMP = "stepOneTargetTempSetFeature"  # confirmed
CMD_STEP2_TEMP = "stepTwoTargetTempSetFeature"
CMD_STEP3_TEMP = "stepThreeTargetTempSetFeature"
CMD_CHILLER_CHILDLOCK = "childlockRemCmdFeature"
CMD_CHILLER_DISP_BRIGHTNESS = "dispBrightnessFeature"

# Standard request headers (sent on every authenticated call)
STANDARD_HEADERS = {
    "x-tenant": TENANT,
    "Content-Type": "application/json;charset=UTF-8",
    "accept-hlsschema": "3.0",
    "Cache-Control": "no-cache",
}

# Oven temperature limits (°C)
OVEN_MIN_TEMP = 30
OVEN_MAX_TEMP = 280
OVEN_TEMP_STEP = 5

# Platforms to set up per config entry
PLATFORMS = ["sensor", "binary_sensor", "switch", "climate", "number"]

# WebSocket reconnect
WS_RECONNECT_MIN_DELAY = 1
WS_RECONNECT_MAX_DELAY = 300
