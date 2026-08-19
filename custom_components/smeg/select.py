"""Select entities for Smeg appliances.

Exposes configurable settings that have a fixed set of options:
  - Temperature format (°C / °F)
  - Clock format (24h / 12h)
  - Weight format (kg / oz)

These correspond to the Display Settings section in both SmegConnect and
SmegConnect Plus apps. The same command codes work for both ovens and blast
chillers (no RemCmd variant needed for format settings).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
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
    # Available options shown in HA (must match API state values exactly,
    # case-insensitive). Extend option_map if the API uses different values.
    select_options: tuple[str, ...] = ()
    # Maps HA option label → API command value when they differ.
    # Leave empty when option label == API value.
    option_map: tuple[tuple[str, str], ...] = ()
    device_types: tuple[int, ...] = ()


SELECT_DESCRIPTIONS: tuple[SmegSelectDescription, ...] = (
    SmegSelectDescription(
        key="temp_format",
        name="Temperature Format",
        state_field="tempFormat",
        command_code=CMD_TEMP_FORMAT,
        param_key="tempFormat",
        # State value from live capture: "°C" — assume command uses same value.
        # If commands fail, try option_map=(("°C","C"),("°F","F")).
        select_options=("°C", "°F"),
        entity_category=EntityCategory.CONFIG,
        device_types=(DEVICE_TYPE_OVEN, DEVICE_TYPE_BLAST_CHILLER),
    ),
    SmegSelectDescription(
        key="clock_format",
        name="Clock Format",
        state_field="hourFormat",
        command_code=CMD_HOUR_FORMAT,
        param_key="hourFormat",
        select_options=("24h", "12h"),
        entity_category=EntityCategory.CONFIG,
        device_types=(DEVICE_TYPE_OVEN, DEVICE_TYPE_BLAST_CHILLER),
    ),
    SmegSelectDescription(
        key="weight_format",
        name="Weight Format",
        state_field="weightFormat",
        command_code=CMD_WEIGHT_FORMAT,
        param_key="weightFormat",
        select_options=("kg", "oz"),
        entity_category=EntityCategory.CONFIG,
        device_types=(DEVICE_TYPE_OVEN, DEVICE_TYPE_BLAST_CHILLER),
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
        self._optimistic_option: str | None = None
        self._option_map = dict(description.option_map)

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
            return None

        sv = str(value)
        # Direct match first
        if sv in self._attr_options:
            return sv
        # Case-insensitive fallback
        for opt in self._attr_options:
            if sv.lower() == opt.lower():
                return opt

        _LOGGER.debug(
            "Unrecognised %s value %r on %s (options: %s)",
            self.entity_description.state_field,
            sv,
            self._device_code,
            self._attr_options,
        )
        return None

    async def async_select_option(self, option: str) -> None:
        desc = self.entity_description
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
