"""Switch entities for Smeg appliances (light, childlock, keepWarm, etc.)."""
from __future__ import annotations

import logging
from dataclasses import dataclass

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CMD_CHILDLOCK,
    CMD_CHILLER_CHILDLOCK,
    CMD_CHILLER_SOUND,
    CMD_ECO_LIGHT,
    CMD_ECO_LOGIC,
    CMD_KEEP_WARM,
    CMD_LIGHT,
    CMD_SOUND,
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
    requires_remote_control: bool = True
    # When True: return False (not None) when state field is absent from device state,
    # producing a toggle UI instead of action-button UI for write-only switches.
    default_off: bool = False
    # When True: invert the state field so that "OFF" in the firmware means the switch
    # is logically On. Used for child lock where the oven/chiller firmware encodes
    # "lock engaged" as childlock="OFF" (i.e. childlock feature is deactivated/cleared).
    invert_state: bool = False
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
        name="Eco Light Mode",
        state_field="ecoLight",
        command_on=CMD_ECO_LIGHT,
        param_key="ecoLight",
        param_value_on="ON",
        param_value_off="OFF",
        requires_remote_control=False,
        entity_category=EntityCategory.CONFIG,
        device_types=(DEVICE_TYPE_OVEN,),
    ),
    SmegSwitchDescription(
        key="eco_logic",
        name="Eco Heating Mode",
        state_field="ecoLogic",
        command_on=CMD_ECO_LOGIC,
        param_key="ecoLogic",
        param_value_on="ON",
        param_value_off="OFF",
        requires_remote_control=False,
        entity_category=EntityCategory.CONFIG,
        device_types=(DEVICE_TYPE_OVEN,),
    ),
    # Oven child lock: firmware uses childlock="OFF" to mean "lock engaged".
    # param_value_on="OFF" → turn switch On (lock engaged) → send childlock=OFF to oven.
    # invert_state=True → show switch On when childlock="OFF" in state (lock engaged).
    SmegSwitchDescription(
        key="childlock",
        name="Child Lock",
        state_field="childlock",
        command_on=CMD_CHILDLOCK,
        param_key="childlock",
        param_value_on="OFF",
        param_value_off="ON",
        invert_state=True,
        requires_remote_control=False,
        device_types=(DEVICE_TYPE_OVEN,),
    ),
    SmegSwitchDescription(
        key="sound",
        name="Sound",
        state_field="soundActiv",
        command_on=CMD_SOUND,
        param_key="soundActiv",
        param_value_on="ON",
        param_value_off="OFF",
        requires_remote_control=False,
        entity_category=EntityCategory.CONFIG,
        device_types=(DEVICE_TYPE_OVEN,),
    ),
    SmegSwitchDescription(
        key="chiller_sound",
        name="Sound",
        state_field="soundActivRemCmd",
        command_on=CMD_CHILLER_SOUND,
        param_key="soundActivRemCmd",
        param_value_on="1",
        param_value_off="0",
        default_off=True,
        requires_remote_control=False,
        entity_category=EntityCategory.CONFIG,
        device_types=(DEVICE_TYPE_BLAST_CHILLER,),
    ),
    # Blast chiller child lock: childlockRemCmd=1 locks, 0 unlocks.
    # Coordinator now synthesises childlock="OFF" when locked (consistent with oven).
    # invert_state=True → show switch On when childlock="OFF" in state (lock engaged).
    SmegSwitchDescription(
        key="chiller_childlock",
        name="Child Lock",
        state_field="childlock",
        command_on=CMD_CHILLER_CHILDLOCK,
        param_key="childlockRemCmd",
        param_value_on="1",
        param_value_off="0",
        invert_state=True,
        requires_remote_control=False,
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
        self._optimistic_on: bool | None = None

    def _handle_coordinator_update(self) -> None:
        """Clear the optimistic cache whenever the coordinator gets real data."""
        self._optimistic_on = None
        super()._handle_coordinator_update()

    @property
    def is_on(self) -> bool | None:
        # Show the commanded state immediately; real state catches up on next poll/push
        if self._optimistic_on is not None:
            return self._optimistic_on
        value = self._state.get(self.entity_description.state_field)
        if value is None:
            # default_off=True: return False so HA renders a toggle (not action buttons)
            # Used for blast chiller switches whose state is in bit arrays, not named fields
            return False if self.entity_description.default_off else None
        raw = str(value).upper() in ("ON", "1", "TRUE")
        return (not raw) if self.entity_description.invert_state else raw

    async def async_turn_on(self, **kwargs) -> None:
        self._check_remote_control()
        await self._send(self.entity_description.param_value_on)
        self._optimistic_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        self._check_remote_control()
        await self._send(self.entity_description.param_value_off)
        self._optimistic_on = False
        self.async_write_ha_state()

    def _check_remote_control(self) -> None:
        if not self.entity_description.requires_remote_control:
            return
        rc = self._state.get("remoteControl", "ON")
        if str(rc).lower() not in ("on", "true", "1"):
            raise HomeAssistantError(
                "Remote control is disabled on this appliance. "
                "Enable it on the appliance display before sending commands."
            )

    async def _send(self, value: str) -> None:
        desc = self.entity_description
        try:
            await self.coordinator.api.send_command(
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
            # Clear optimistic state on failure so we don't show wrong state
            self._optimistic_on = None
            self.async_write_ha_state()
