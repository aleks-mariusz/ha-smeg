"""Select entities for Smeg appliances.

Display Settings screen in both SmegConnect and SmegConnect Plus:
  - Temperature Format (°C / °F)
  - Clock Format (24h / 12h)
  - Weight Format (kg / oz)

Important: oven and blast chiller use DIFFERENT value formats for these fields.
  Oven:          state = "°C" / "°F" (string), command value = "°C" / "°F"
  Blast chiller: state = 0 / 1 (integer),      command value = "0" / "1"

Confirmed from live SmegConnect Plus command capture:
  tempFormatFeature  parameterKey: tempFormat  value: "0" (°C) or "1" (°F)
  digClockRemCmdFeature confirmed for digital clock (same integer "0"/"1" pattern)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CMD_CHILLER_DIGITAL_CLOCK,
    CMD_DIGITAL_CLOCK,
    CMD_HOUR_FORMAT,
    CMD_TEMP_FORMAT,
    CMD_WEIGHT_FORMAT,
    DEVICE_TYPE_BLAST_CHILLER,
    DEVICE_TYPE_OVEN,
    DOMAIN,
)
from .coordinator import SmegCoordinator
from .entity import SmegEntity

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class SmegSelectDescription(SelectEntityDescription):
    """Extends SelectEntityDescription with Smeg-specific fields."""

    state_field: str = ""
    command_code: str = ""
    param_key: str = ""
    # Available option labels shown in HA UI
    select_options: tuple[str, ...] = ()
    # Maps: raw state value (as string, after str()) → HA option label.
    # Empty = state string IS the option label (direct match, case-insensitive).
    state_map: tuple[tuple[str, str], ...] = ()
    # Maps: HA option label → API command value.
    # Empty = option label IS the command value.
    option_map: tuple[tuple[str, str], ...] = ()
    # Returned when the state field is absent from the device state (None = Unknown).
    # Use for devices where state is in bit arrays, not named fields.
    default_option: str | None = None
    device_types: tuple[int, ...] = ()


SELECT_DESCRIPTIONS: tuple[SmegSelectDescription, ...] = (
    # --- Clock Font (oven: state="OFF"/"ON", chiller: digClock absent from v1 state) ---
    # Replaces the previous "Clock Display" boolean switch with a descriptive dropdown.
    # "Normal" = digClock OFF (standard clock style)
    # "Digital" = digClock ON  (digital LED-style clock)
    SmegSelectDescription(
        key="clock_font",
        name="Clock Font",
        state_field="digClock",
        command_code=CMD_DIGITAL_CLOCK,
        param_key="digClock",
        select_options=("Normal", "Digital"),
        state_map=(("OFF", "Normal"), ("ON", "Digital")),
        option_map=(("Normal", "OFF"), ("Digital", "ON")),
        entity_category=EntityCategory.CONFIG,
        device_types=(DEVICE_TYPE_OVEN,),
    ),
    # Blast chiller: digClock absent from v1 state (bit arrays) — command works but
    # state can't be read back. Default to "Normal" (off = standard font) so the
    # select shows a sensible initial value rather than Unknown.
    SmegSelectDescription(
        key="clock_font",
        name="Clock Font",
        state_field="digClock",
        command_code=CMD_CHILLER_DIGITAL_CLOCK,
        param_key="digClockRemCmd",
        select_options=("Normal", "Digital"),
        state_map=(("0", "Normal"), ("1", "Digital")),
        option_map=(("Normal", "0"), ("Digital", "1")),
        default_option="Normal",
        entity_category=EntityCategory.CONFIG,
        device_types=(DEVICE_TYPE_BLAST_CHILLER,),
    ),

    # --- Oven (string state and string command values) ---
    SmegSelectDescription(
        key="temp_format",
        name="Temperature Format",
        state_field="tempFormat",
        command_code=CMD_TEMP_FORMAT,
        param_key="tempFormat",
        select_options=("°C", "°F"),
        # Oven state returns "°C" or "°F" (Unicode °). Direct match works.
        entity_category=EntityCategory.CONFIG,
        device_types=(DEVICE_TYPE_OVEN,),
    ),
    SmegSelectDescription(
        key="clock_format",
        name="Clock Format",
        state_field="hourFormat",
        command_code=CMD_HOUR_FORMAT,
        param_key="hourFormat",
        select_options=("24h", "12h"),
        entity_category=EntityCategory.CONFIG,
        device_types=(DEVICE_TYPE_OVEN,),
    ),
    SmegSelectDescription(
        key="weight_format",
        name="Weight Format",
        state_field="weightFormat",
        command_code=CMD_WEIGHT_FORMAT,
        param_key="weightFormat",
        select_options=("kg", "oz"),
        entity_category=EntityCategory.CONFIG,
        device_types=(DEVICE_TYPE_OVEN,),
    ),

    # --- Blast chiller (integer state, string "0"/"1" command values) ---
    # Confirmed from SmegConnect Plus live capture: tempFormatFeature with value "0" = °C.
    SmegSelectDescription(
        key="temp_format",
        name="Temperature Format",
        state_field="tempFormat",
        command_code=CMD_TEMP_FORMAT,
        param_key="tempFormat",
        select_options=("°C", "°F"),
        state_map=(("0", "°C"), ("1", "°F")),
        option_map=(("°C", "0"), ("°F", "1")),
        entity_category=EntityCategory.CONFIG,
        device_types=(DEVICE_TYPE_BLAST_CHILLER,),
    ),
    SmegSelectDescription(
        key="clock_format",
        name="Clock Format",
        state_field="hourFormat",
        command_code=CMD_HOUR_FORMAT,
        param_key="hourFormat",
        select_options=("24h", "12h"),
        state_map=(("0", "24h"), ("1", "12h")),
        option_map=(("24h", "0"), ("12h", "1")),
        entity_category=EntityCategory.CONFIG,
        device_types=(DEVICE_TYPE_BLAST_CHILLER,),
    ),
    SmegSelectDescription(
        key="weight_format",
        name="Weight Format",
        state_field="weightFormat",
        command_code=CMD_WEIGHT_FORMAT,
        param_key="weightFormat",
        select_options=("kg", "oz"),
        state_map=(("0", "kg"), ("1", "oz")),
        option_map=(("kg", "0"), ("oz", "1")),
        entity_category=EntityCategory.CONFIG,
        device_types=(DEVICE_TYPE_BLAST_CHILLER,),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: SmegCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SmegSelectEntity] = []

    for device_code, device in coordinator.data.items():
        type_id = device.get("deviceTypeId", 0)
        for desc in SELECT_DESCRIPTIONS:
            if type_id in desc.device_types:
                entities.append(SmegSelectEntity(coordinator, device_code, desc))

    async_add_entities(entities)


class SmegSelectEntity(SmegEntity, SelectEntity):
    """A select entity for a Smeg configurable setting."""

    entity_description: SmegSelectDescription

    def __init__(
        self,
        coordinator: SmegCoordinator,
        device_code: str,
        description: SmegSelectDescription,
    ) -> None:
        super().__init__(coordinator, device_code)
        self.entity_description = description
        self._attr_unique_id = f"{device_code}_{description.key}"
        self._attr_options = list(description.select_options)
        self._state_map = dict(description.state_map)
        self._option_map = dict(description.option_map)
        self._optimistic_option: str | None = None
        self._default_option = description.default_option

    def _handle_coordinator_update(self) -> None:
        """Clear optimistic state when coordinator delivers real data."""
        self._optimistic_option = None
        super()._handle_coordinator_update()

    @property
    def current_option(self) -> str | None:
        if self._optimistic_option is not None:
            return self._optimistic_option

        value = self._state.get(self.entity_description.state_field)
        if value is None:
            return self._default_option  # None → Unknown, or a fallback like "Normal"

        sv = str(value)

        # Try state_map first (integer→label, e.g. "0" → "°C" for blast chiller)
        if sv in self._state_map:
            return self._state_map[sv]

        # Try direct match
        if sv in self._attr_options:
            return sv

        # Case-insensitive fallback
        for opt in self._attr_options:
            if sv.lower() == opt.lower():
                return opt

        _LOGGER.debug(
            "Unrecognised %s value %r on %s (options: %s, state_map: %s)",
            self.entity_description.state_field,
            sv,
            self._device_code,
            self._attr_options,
            self._state_map,
        )
        return None

    async def async_select_option(self, option: str) -> None:
        desc = self.entity_description
        # Use option_map for devices that use integer command values (blast chiller)
        api_value = self._option_map.get(option, option)
        try:
            await self.coordinator.api.send_command(
                self._device_code,
                self._device.get("deviceTypeId", 7),
                desc.command_code,
                [{"parameterKey": desc.param_key, "parameterValue": api_value}],
            )
            self._optimistic_option = option
            self.async_write_ha_state()
        except Exception:
            _LOGGER.error(
                "Failed to set %s to %r on %s",
                desc.param_key,
                option,
                self._device_code,
                exc_info=True,
            )
