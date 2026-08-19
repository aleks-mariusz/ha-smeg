"""Switch entities for Smeg appliances (light, childlock, keepWarm, etc.)."""
from __future__ import annotations

import logging
from dataclasses import dataclass

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CMD_CHILDLOCK,
    CMD_CHILLER_CHILDLOCK,
    CMD_ECO_LIGHT,
    CMD_ECO_LOGIC,
    CMD_KEEP_WARM,
    CMD_LIGHT,
    DEVICE_TYPE_BLAST_CHILLER,
    DEVICE_TYPE_OVEN,
    DOMAIN,
)
from .coordinator import SmegCoordinator
from .entity import SmegEntity

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class SmegSwitchDescription(SwitchEntityDescription):
    state_field: str = ""
    command_on: str = ""
    param_key: str = ""
    param_value_on: str = "ON"
    param_value_off: str = "OFF"
    device_types: tuple[int, ...] = ()


SWITCH_DESCRIPTIONS: tuple[SmegSwitchDescription, ...] = (
    SmegSwitchDescription(
        key="light",
        name="Light",
        state_field="light",
        command_on=CMD_LIGHT,
        param_key="light",
        param_value_on="ON",
        param_value_off="OFF",
        device_types=(DEVICE_TYPE_OVEN,),
    ),
    SmegSwitchDescription(
        key="keep_warm",
        name="Keep Warm",
        state_field="keepWarm",
        command_on=CMD_KEEP_WARM,
        param_key="keepWarm",
        param_value_on="ON",
        param_value_off="OFF",
        device_types=(DEVICE_TYPE_OVEN,),
    ),
    SmegSwitchDescription(
        key="eco_light",
        name="Eco Light",
        state_field="ecoLight",
        command_on=CMD_ECO_LIGHT,
        param_key="ecoLight",
        param_value_on="ON",
        param_value_off="OFF",
        device_types=(DEVICE_TYPE_OVEN,),
    ),
    SmegSwitchDescription(
        key="eco_logic",
        name="Eco Logic",
        state_field="ecoLogic",
        command_on=CMD_ECO_LOGIC,
        param_key="ecoLogic",
        param_value_on="ON",
        param_value_off="OFF",
        device_types=(DEVICE_TYPE_OVEN,),
    ),
    SmegSwitchDescription(
        key="childlock",
        name="Child Lock",
        state_field="childlock",
        command_on=CMD_CHILDLOCK,
        param_key="childlock",
        param_value_on="ON",
        param_value_off="OFF",
        device_types=(DEVICE_TYPE_OVEN,),
    ),
    SmegSwitchDescription(
        key="chiller_childlock",
        name="Child Lock",
        state_field="childlock",
        command_on=CMD_CHILLER_CHILDLOCK,
        param_key="childlock",
        # Blast chiller childlock uses "1"/"0" per the protocol doc pattern
        param_value_on="1",
        param_value_off="0",
        device_types=(DEVICE_TYPE_BLAST_CHILLER,),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: SmegCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SmegSwitchEntity] = []

    for device_code, device in coordinator.data.items():
        type_id = device.get("deviceTypeId", 0)
        for desc in SWITCH_DESCRIPTIONS:
            if type_id in desc.device_types:
                entities.append(SmegSwitchEntity(coordinator, device_code, desc))

    async_add_entities(entities)


class SmegSwitchEntity(SmegEntity, SwitchEntity):
    """A switch entity for a toggleable Smeg feature."""

    entity_description: SmegSwitchDescription

    def __init__(
        self,
        coordinator: SmegCoordinator,
        device_code: str,
        description: SmegSwitchDescription,
    ) -> None:
        super().__init__(coordinator, device_code)
        self.entity_description = description
        self._attr_unique_id = f"{device_code}_{description.key}"

    @property
    def is_on(self) -> bool | None:
        value = self._state.get(self.entity_description.state_field)
        if value is None:
            return None
        # Handle both "ON"/"OFF" and "1"/"0" style values
        return str(value).upper() in ("ON", "1", "TRUE")

    async def async_turn_on(self, **kwargs) -> None:
        await self._send(self.entity_description.param_value_on)

    async def async_turn_off(self, **kwargs) -> None:
        await self._send(self.entity_description.param_value_off)

    async def _send(self, value: str) -> None:
        desc = self.entity_description
        try:
            await api.send_command(
                self._device_code,
                self._device.get("deviceTypeId", 7),
                desc.command_on,
                [{"parameterKey": desc.param_key, "parameterValue": value}],
            )
        except Exception:
            _LOGGER.error(
                "Failed to send %s=%s to %s", desc.command_on, value, self._device_code,
                exc_info=True,
            )
