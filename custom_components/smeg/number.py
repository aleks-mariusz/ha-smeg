"""Number entities for Smeg appliances (timers, brightness, blast chiller step temps)."""
from __future__ import annotations

import logging
from dataclasses import dataclass

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CMD_DISP_BRIGHTNESS,
    CMD_STEP1_TEMP,
    CMD_STEP2_TEMP,
    CMD_STEP3_TEMP,
    CMD_TIMER1,
    CMD_TIMER2,
    CMD_TIMER3,
    DEVICE_TYPE_BLAST_CHILLER,
    DEVICE_TYPE_OVEN,
    DOMAIN,
)
from .coordinator import SmegCoordinator
from .entity import SmegEntity

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class SmegNumberDescription(NumberEntityDescription):
    state_field: str = ""
    command_code: str = ""
    param_key: str = ""
    device_types: tuple[int, ...] = ()


NUMBER_DESCRIPTIONS: tuple[SmegNumberDescription, ...] = (
    # --- Oven numbers ---
    SmegNumberDescription(
        key="timer1",
        name="Timer 1",
        state_field="timer1",
        command_code=CMD_TIMER1,
        param_key="timer1",
        native_min_value=0,
        native_max_value=86400,
        native_step=60,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        device_class=NumberDeviceClass.DURATION,
        mode=NumberMode.BOX,
        device_types=(DEVICE_TYPE_OVEN,),
    ),
    SmegNumberDescription(
        key="timer2",
        name="Timer 2",
        state_field="timer2",
        command_code=CMD_TIMER2,
        param_key="timer2",
        native_min_value=0,
        native_max_value=86400,
        native_step=60,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        device_class=NumberDeviceClass.DURATION,
        mode=NumberMode.BOX,
        device_types=(DEVICE_TYPE_OVEN,),
    ),
    SmegNumberDescription(
        key="timer3",
        name="Timer 3",
        state_field="timer3",
        command_code=CMD_TIMER3,
        param_key="timer3",
        native_min_value=0,
        native_max_value=86400,
        native_step=60,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        device_class=NumberDeviceClass.DURATION,
        mode=NumberMode.BOX,
        device_types=(DEVICE_TYPE_OVEN,),
    ),
    SmegNumberDescription(
        key="display_brightness",
        name="Display Brightness",
        state_field="dispBrightness",
        command_code=CMD_DISP_BRIGHTNESS,
        param_key="dispBrightness",
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        mode=NumberMode.SLIDER,
        device_types=(DEVICE_TYPE_OVEN,),
    ),
    # --- Blast chiller numbers ---
    SmegNumberDescription(
        key="step1_target_temp",
        name="Step 1 Target Temperature",
        state_field="stepOneTargetTempSet",
        command_code=CMD_STEP1_TEMP,
        param_key="stepOneTargetTempSet",
        native_min_value=-40,
        native_max_value=10,
        native_step=1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=NumberDeviceClass.TEMPERATURE,
        mode=NumberMode.BOX,
        device_types=(DEVICE_TYPE_BLAST_CHILLER,),
    ),
    SmegNumberDescription(
        key="step2_target_temp",
        name="Step 2 Target Temperature",
        state_field="stepTwoTargetTempSet",
        command_code=CMD_STEP2_TEMP,
        param_key="stepTwoTargetTempSet",
        native_min_value=-40,
        native_max_value=10,
        native_step=1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=NumberDeviceClass.TEMPERATURE,
        mode=NumberMode.BOX,
        device_types=(DEVICE_TYPE_BLAST_CHILLER,),
    ),
    SmegNumberDescription(
        key="step3_target_temp",
        name="Step 3 Target Temperature",
        state_field="stepThreeTargetTempSet",
        command_code=CMD_STEP3_TEMP,
        param_key="stepThreeTargetTempSet",
        native_min_value=-40,
        native_max_value=10,
        native_step=1,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=NumberDeviceClass.TEMPERATURE,
        mode=NumberMode.BOX,
        device_types=(DEVICE_TYPE_BLAST_CHILLER,),
    ),
    SmegNumberDescription(
        key="chiller_display_brightness",
        name="Display Brightness",
        state_field="dispBrightness",
        command_code=CMD_DISP_BRIGHTNESS,
        param_key="dispBrightness",
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        mode=NumberMode.SLIDER,
        device_types=(DEVICE_TYPE_BLAST_CHILLER,),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: SmegCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SmegNumberEntity] = []

    for device_code, device in coordinator.data.items():
        type_id = device.get("deviceTypeId", 0)
        for desc in NUMBER_DESCRIPTIONS:
            if type_id in desc.device_types:
                entities.append(SmegNumberEntity(coordinator, device_code, desc))

    async_add_entities(entities)


class SmegNumberEntity(SmegEntity, NumberEntity):
    """A number entity for a writable Smeg numeric field."""

    entity_description: SmegNumberDescription

    def __init__(
        self,
        coordinator: SmegCoordinator,
        device_code: str,
        description: SmegNumberDescription,
    ) -> None:
        super().__init__(coordinator, device_code)
        self.entity_description = description
        self._attr_unique_id = f"{device_code}_{description.key}"

    @property
    def native_value(self) -> float | None:
        val = self._state.get(self.entity_description.state_field)
        try:
            return float(val)
        except (TypeError, ValueError):
            return None

    async def async_set_native_value(self, value: float) -> None:
        desc = self.entity_description
        try:
            await self.coordinator.api.send_command(
                self._device_code,
                self._device.get("deviceTypeId", 7),
                desc.command_code,
                [{"parameterKey": desc.param_key, "parameterValue": int(value)}],
            )
        except Exception:
            _LOGGER.error(
                "Failed to set %s to %s on %s", desc.param_key, value, self._device_code,
                exc_info=True,
            )
