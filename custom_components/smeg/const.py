"""Constants for the SmegConnect integration."""
from __future__ import annotations

DOMAIN = "smeg"

API_BASE = "https://smegcons.prod-platform.smegconnect.com"
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

# Internal modelNumber → (commercial_code, display_description) for all 80
# SmegConnect/SmegConnect Plus supported appliances.
#
# Internal modelNumbers sourced directly from the SmegConnect Plus app's
# categories.json asset (extracted from base.apk). Commercial codes and
# product descriptions from smeg.com/smeg-connect/all-products and the
# SmegConnect APK's applCommCode field mappings.
#
# Keys  = internal modelNumber from GET /api/v1/devices (e.g. "0000491139")
# Values = (commercial_code, display_description)
# commercial_code = what "Model" shows in the app's Product/Info tab
#
# To add an unlisted model: provision it, note the CBapplianceModelId from
# the /info status field, read commercial code from the app Product tab,
# look it up in Smeg's catalogue, then add an entry here.
SMEG_MODELS: dict[str, tuple[str, str]] = {

    # -----------------------------------------------------------------------
    # Blast Chillers
    # -----------------------------------------------------------------------
    "0000781592": ("SBC4604WNR",  "Multisense Blast Chiller / 45 cm / Dolce Stil Novo"),   # earlier firmware
    "0000781784": ("SBC4604WNR1", "Multisense Blast Chiller / 45 cm / Dolce Stil Novo"),   # confirmed ✓
    "0000781785": ("SBC4104WG",   "Blast Chiller / 45 cm / Dolce Stil Novo"),
    "0000781786": ("SBC4104WB3",  "Blast Chiller / 45 cm / Dolce Stil Novo"),
    "0000781787": ("SBC4304WX",   "Multisense Blast Chiller / 45 cm / Classica"),

    # -----------------------------------------------------------------------
    # Dishwashers
    # -----------------------------------------------------------------------
    "0000136167": ("STL324BQLLW",  "Fully-integrated Dishwasher / 60 cm"),
    "0000136258": ("STL7324AQLLW", "Fully-integrated Dishwasher / 60 cm"),
    "0000136262": ("STL7324BLW",   "Fully-integrated Dishwasher / 60 cm"),

    # -----------------------------------------------------------------------
    # Galileo Oven series — Dolce Stil Novo
    # SO/SOP prefix: newer Galileo platform (Omnichef, SteamOne, Steam100 Pro, Speedwave)
    # -----------------------------------------------------------------------
    # 60 cm
    "0000491139": ("SOP6606WS2PNR",  "Pyrolytic SteamOne Oven / 60 cm / Dolce Stil Novo"),  # confirmed ✓
    "0000491151": ("SOPA6606WS2PNR", "Pyrolytic SteamOne Oven / 60 cm / Dolce Stil Novo"),
    "0000491087": ("SO6606WAPNR",    "Omnichef Oven / 60 cm / Dolce Stil Novo"),
    "0000491150": ("SOA6606WAPNR",   "Omnichef Oven / 60 cm / Dolce Stil Novo"),
    "0000491138": ("SO6606WS4PNR",   "Steam100 Pro Oven / 60 cm / Dolce Stil Novo"),
    "0000491158": ("SOA6606WS4PNR",  "Steam100 Pro Oven / 60 cm / Dolce Stil Novo"),
    "0000491152": ("SOA6606WM2PNR",  "Speedwave Oven / 60 cm / Dolce Stil Novo"),
    # 45 cm compact
    "0000410008": ("SO4606WAPNR",    "Omnichef Oven / 45 cm compact / Dolce Stil Novo"),    # confirmed ✓
    "0000410009": ("SOA4606WAPNR",   "Omnichef Oven / 45 cm compact / Dolce Stil Novo"),
    "0000440171": ("SO4606WS4PNR",   "Steam100 Pro Oven / 45 cm compact / Dolce Stil Novo"),
    "0000560436": ("SO4606WM2PNR",   "Speedwave Oven / 45 cm compact / Dolce Stil Novo"),
    "0000560432": ("SOA4606WM2PNR",  "Speedwave Oven / 45 cm compact / Dolce Stil Novo"),
    # Linea aesthetic — 60 cm
    "0000491272": ("SO6106WAPG",     "Omnichef Oven / 60 cm / Linea"),
    "0000491273": ("SO6106WAPB3",    "Omnichef Oven / 60 cm / Linea"),
    # Linea aesthetic — 45 cm compact
    "0000410017": ("SO4106WAPG",     "Omnichef Oven / 45 cm compact / Linea"),
    "0000410018": ("SO4106WAPB3",    "Omnichef Oven / 45 cm compact / Linea"),

    # -----------------------------------------------------------------------
    # SFP Pyrolytic + Steam Oven series — Dolce Stil Novo / Linea
    # SFP prefix: pyrolytic + steam (WSP) or thermo-pyrolytic (WTP)
    # -----------------------------------------------------------------------
    # 90 cm
    "0000500142": ("SFPR9606WTPNR",  "Pyrolytic Oven / 90 cm / Dolce Stil Novo"),
    "0000500164": ("SFPRA9606WTPNR", "Pyrolytic Oven / 90 cm / Dolce Stil Novo"),
    "0000500139": ("SFP9305WSPX",    "Pyrolytic Steam Oven / 90 cm / Classica"),
    # 60 cm — Dolce Stil Novo
    "0000490989": ("SFP6606WSPNR",   "Pyrolytic Steam Oven / 60 cm / Dolce Stil Novo"),
    "0000491009": ("SFP6606WSPNX",   "Pyrolytic Steam Oven / 60 cm / Dolce Stil Novo"),
    "0000491001": ("SFP6606WTPNR",   "Pyrolytic Oven / 60 cm / Dolce Stil Novo"),
    "0000491002": ("SFP6606WTPNX",   "Pyrolytic Oven / 60 cm / Dolce Stil Novo"),
    # 60 cm — Classica
    "0000491036": ("SFP6303WTPX",    "Pyrolytic Oven / 60 cm / Classica"),
    # 45 cm compact — Dolce Stil Novo
    "0000491042": ("SFP6604WSPNR",   "Pyrolytic Steam Oven / 45 cm compact / Dolce Stil Novo"),
    "0000491043": ("SFP6604WSPNX",   "Pyrolytic Steam Oven / 45 cm compact / Dolce Stil Novo"),
    "0000491044": ("SFP6604WTPNR",   "Pyrolytic Oven / 45 cm compact / Dolce Stil Novo"),
    "0000491045": ("SFP6604WTPNX",   "Pyrolytic Oven / 45 cm compact / Dolce Stil Novo"),
    "0000451339": ("SFP6104WTPB",    "Pyrolytic Oven / 45 cm compact / Dolce Stil Novo"),
    "0000451340": ("SFP6104WTPN",    "Pyrolytic Oven / 45 cm compact / Dolce Stil Novo"),
    # 45 cm compact — Linea
    "0000491034": ("SFP6106WSPS",    "Pyrolytic Steam Oven / 45 cm compact / Linea"),
    "0000491003": ("SFP6106WTPS",    "Pyrolytic Oven / 45 cm compact / Linea"),
    "0000491040": ("SFP6104WTPS",    "Pyrolytic Oven / 45 cm compact / Linea"),

    # -----------------------------------------------------------------------
    # SF Pyrolytic Oven series — 45 cm compact
    # SF4 prefix: WVCP = ventilated pyrolytic, WMC = multifunction combi
    # -----------------------------------------------------------------------
    # Dolce Stil Novo
    "0000440148": ("SF4606WVCPNR",  "Pyrolytic Oven / 45 cm compact / Dolce Stil Novo"),
    "0000440144": ("SF4606WVCPNX",  "Pyrolytic Oven / 45 cm compact / Dolce Stil Novo"),
    "0000440160": ("SF4604WVCPNR",  "Pyrolytic Oven / 45 cm compact / Dolce Stil Novo"),
    "0000440161": ("SF4604WVCPNX",  "Pyrolytic Oven / 45 cm compact / Dolce Stil Novo"),
    "0000560339": ("SF4606WMCNR",   "Multifunction Oven / 45 cm compact / Dolce Stil Novo"),
    "0000560356": ("SF4606WMCNX",   "Multifunction Oven / 45 cm compact / Dolce Stil Novo"),
    "0000560377": ("SF4604WMCNR",   "Multifunction Oven / 45 cm compact / Dolce Stil Novo"),
    "0000560378": ("SF4604WMCNX",   "Multifunction Oven / 45 cm compact / Dolce Stil Novo"),
    "0000560418": ("SF4604WMCNRK",  "Multifunction Oven / 45 cm compact / Dolce Stil Novo"),
    # Linea
    "0000440147": ("SF4106WVCPS",   "Pyrolytic Oven / 45 cm compact / Linea"),
    "0000440157": ("SF4104WVCPS",   "Pyrolytic Oven / 45 cm compact / Linea"),
    "0000440158": ("SF4104WVCPN",   "Pyrolytic Oven / 45 cm compact / Linea"),
    "0000560350": ("SF4106WMCS",    "Multifunction Oven / 45 cm compact / Linea"),
    "0000560374": ("SF4104WMCN",    "Multifunction Oven / 45 cm compact / Linea"),
    "0000560375": ("SF4104WMCS",    "Multifunction Oven / 45 cm compact / Linea"),
    # Classica
    "0000440159": ("SF4303WVCPX",   "Pyrolytic Oven / 45 cm compact / Classica"),
    "0000560376": ("SF4303WMCX",    "Multifunction Oven / 45 cm compact / Classica"),

    # -----------------------------------------------------------------------
    # Wine Coolers (CVI series) — built-in
    # -----------------------------------------------------------------------
    # Dolce Stil Novo — 82 cm tall (38 bottles)
    "0000752711": ("CVI638LWN3",  "Built-in Wine Cooler / 82 cm / Dolce Stil Novo"),
    "0000752712": ("CVI638RWN3",  "Built-in Wine Cooler / 82 cm / Dolce Stil Novo"),
    "0000752306": ("CVI638LWN2",  "Built-in Wine Cooler / 82 cm / Dolce Stil Novo"),
    "0000752307": ("CVI638RWN2",  "Built-in Wine Cooler / 82 cm / Dolce Stil Novo"),
    # Dolce Stil Novo — 45 cm compact (21 bottles)
    "0000752707": ("CVI621LWNR3", "Built-in Wine Cooler / 45 cm compact / Dolce Stil Novo"),
    "0000752708": ("CVI621LWNX3", "Built-in Wine Cooler / 45 cm compact / Dolce Stil Novo"),
    "0000752709": ("CVI621RWNR3", "Built-in Wine Cooler / 45 cm compact / Dolce Stil Novo"),
    "0000752710": ("CVI621RWNX3", "Built-in Wine Cooler / 45 cm compact / Dolce Stil Novo"),
    # Dolce Stil Novo — standard height (18 bottles)
    "0000752302": ("CVI618LWNX2", "Built-in Wine Cooler / 60 cm / Dolce Stil Novo"),
    "0000752303": ("CVI618RWNX2", "Built-in Wine Cooler / 60 cm / Dolce Stil Novo"),
    "0000752304": ("CVI618LWNR2", "Built-in Wine Cooler / 60 cm / Dolce Stil Novo"),
    "0000752305": ("CVI618RWNR2", "Built-in Wine Cooler / 60 cm / Dolce Stil Novo"),
    # Classica — 45 cm (38 bottles)
    "0000752308": ("CVI338LWX2",  "Built-in Wine Cooler / 45 cm compact / Classica"),
    "0000752309": ("CVI338RWX2",  "Built-in Wine Cooler / 45 cm compact / Classica"),
    # Linea — compact
    "0000752388": ("CVI138LWS2",  "Built-in Wine Cooler / compact / Linea"),
    "0000752389": ("CVI138RWS2",  "Built-in Wine Cooler / compact / Linea"),
    "0000752286": ("CVI118RWS2",  "Built-in Wine Cooler / compact / Linea"),
    "0000752287": ("CVI118LWS2",  "Built-in Wine Cooler / compact / Linea"),
    # Dolce Stil Novo — compact
    "0000752290": ("CVI118RWN2",  "Built-in Wine Cooler / compact / Dolce Stil Novo"),
    "0000752291": ("CVI118LWN2",  "Built-in Wine Cooler / compact / Dolce Stil Novo"),
    # Classica — standard
    "0000752258": ("CVI318RWX2",  "Built-in Wine Cooler / 45 cm / Classica"),
    "0000752259": ("CVI318LWX2",  "Built-in Wine Cooler / 45 cm / Classica"),
}

def smeg_device_name(model_number: str) -> str:
    """Return the HA device display name for a given API modelNumber.

    Format: 'Smeg {description} ({commercial_code})'
    e.g.   'Smeg Pyrolytic SteamOne Oven / 60 cm / Dolce Stil Novo (SOP6606WS2PNR)'

    Falls back to 'Smeg {model_number}' for unknown models.
    """
    entry = SMEG_MODELS.get(model_number)
    if entry:
        commercial_code, description = entry
        return f"Smeg {description} ({commercial_code})"
    # Unknown model — use the raw model number so it's still unique
    return f"Smeg {model_number}" if model_number else "Smeg Appliance"

# Command version per device type (confirmed from Charles captures)
DEVICE_TYPE_COMMAND_VERSION: dict[int, str] = {
    DEVICE_TYPE_OVEN: "4.0",
    DEVICE_TYPE_BLAST_CHILLER: "4.0",
    DEVICE_TYPE_DISHWASHER: "3.0",
    DEVICE_TYPE_WINE_CHILLER: "3.0",
}

# Oven command codes
CMD_POWER_ON = "Sys_OpSetPowerOnFeature"   # also used for set-temperature; confirmed
CMD_POWER_OFF = "Sys_OpSetPowerOffFeature"
CMD_LIGHT = "lightFeature"                 # confirmed from Charles captures
CMD_KEEP_WARM = "keepWarmFeature"
CMD_ECO_LIGHT = "ecoLightFeature"
CMD_ECO_LOGIC = "ecoLogicFeature"
CMD_CHILDLOCK = "childlockFeature"
CMD_SOUND = "soundActivFeature"
CMD_DIGITAL_CLOCK = "digClockFeature"
CMD_TIMER1 = "timer1Feature"
CMD_TIMER2 = "timer2Feature"
CMD_TIMER3 = "timer3Feature"
CMD_DISP_BRIGHTNESS = "dispBrightnessFeature"

# Blast chiller command codes (RemCmd suffix → "1"/"0" values, different from oven)
CMD_SEQ_START = "currSeqStartCmd"
CMD_SEQ_STOP = "currSeqStopCmd"
CMD_STEP1_TEMP = "stepOneTargetTempSetFeature"   # confirmed
CMD_STEP2_TEMP = "stepTwoTargetTempSetFeature"
CMD_STEP3_TEMP = "stepThreeTargetTempSetFeature"
CMD_CHILLER_CHILDLOCK = "childlockRemCmdFeature"
CMD_CHILLER_SOUND = "soundActivRemCmdFeature"
CMD_CHILLER_DIGITAL_CLOCK = "digClockRemCmdFeature"   # confirmed param: digClockRemCmd

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
