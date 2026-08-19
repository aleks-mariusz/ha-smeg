"""Sensor entities for Smeg appliances."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DEVICE_TYPE_BLAST_CHILLER, DEVICE_TYPE_OVEN, DOMAIN
from .coordinator import SmegCoordinator
from .entity import SmegEntity


@dataclass(frozen=True, kw_only=True)
class SmegSensorDescription(SensorEntityDescription):
    """Extends SensorEntityDescription with Smeg-specific fields."""

    state_field: str = ""
    device_types: tuple[int, ...] = ()


SENSOR_DESCRIPTIONS: tuple[SmegSensorDescription, ...] = (
    # --- Oven sensors ---
    SmegSensorDescription(
        key="cavity_temperature",
        name="Cavity Temperature",
        state_field="currTempOven",
        device_types=(DEVICE_TYPE_OVEN,),
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SmegSensorDescription(
        key="target_temperature",
        name="Target Temperature",
        state_field="currStepTargetTempSet",
        device_types=(DEVICE_TYPE_OVEN,),
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SmegSensorDescription(
        key="cook_elapsed",
        name="Cooking Elapsed Time",
        state_field="currSeqElapsedTime",
        device_types=(DEVICE_TYPE_OVEN,),
        native_unit_of_measurement=UnitOfTime.SECONDS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SmegSensorDescription(
        key="cook_remaining",
        name="Cooking Remaining Time",
        state_field="currSeqDuration",
        device_types=(DEVICE_TYPE_OVEN,),
        native_unit_of_measurement=UnitOfTime.SECONDS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SmegSensorDescription(
        key="cook_phase",
        name="Cooking Phase",
        state_field="currStepCookingPhase",
        device_types=(DEVICE_TYPE_OVEN,),
    ),
    SmegSensorDescription(
        key="error",
        name="Error",
        state_field="failureLabel",
        device_types=(DEVICE_TYPE_OVEN,),
    ),
    SmegSensorDescription(
        key="wifi_signal",
        name="Wi-Fi Signal",
        state_field="CBWiFiLevel",
        device_types=(DEVICE_TYPE_OVEN, DEVICE_TYPE_BLAST_CHILLER),
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
    ),
    SmegSensorDescription(
        key="cb_temperature",
        name="Connectivity Board Temperature",
        state_field="CBtemperaure",   # note: typo is in the firmware field name
        device_types=(DEVICE_TYPE_OVEN,),
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
    ),
    # --- Blast chiller sensors ---
    SmegSensorDescription(
        key="cavity_temperature",
        name="Cavity Temperature",
        state_field="currTempCavity",
        device_types=(DEVICE_TYPE_BLAST_CHILLER,),
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SmegSensorDescription(
        key="chiller_cb_temperature",
        name="Connectivity Board Temperature",
        state_field="CBtemperature",
        device_types=(DEVICE_TYPE_BLAST_CHILLER,),
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
    ),
    SmegSensorDescription(
        key="compressor_runtime",
        name="Compressor Runtime",
        state_field="compressorWorkTime",
        device_types=(DEVICE_TYPE_BLAST_CHILLER,),
        native_unit_of_measurement=UnitOfTime.SECONDS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_registry_enabled_default=False,
    ),
    SmegSensorDescription(
        key="step1_target_temp",
        name="Step 1 Target Temperature",
        state_field="stepOneTargetTempSet",
        device_types=(DEVICE_TYPE_BLAST_CHILLER,),
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    SmegSensorDescription(
        key="meat_probe_temperature",
        name="Meat Probe Temperature",
        state_field="currTempMeatProbe",
        device_types=(DEVICE_TYPE_OVEN, DEVICE_TYPE_BLAST_CHILLER),
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: SmegCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SmegSensorEntity] = []

    for device_code, device in coordinator.data.items():
        type_id = device.get("deviceTypeId", 0)
        for desc in SENSOR_DESCRIPTIONS:
            if type_id in desc.device_types:
                entities.append(SmegSensorEntity(coordinator, device_code, desc))

    async_add_entities(entities)


class SmegSensorEntity(SmegEntity, SensorEntity):
    """A sensor entity for a Smeg appliance state field."""

    entity_description: SmegSensorDescription

    def __init__(
        self,
        coordinator: SmegCoordinator,
        device_code: str,
        description: SmegSensorDescription,
    ) -> None:
        super().__init__(coordinator, device_code)
        self.entity_description = description
        self._attr_unique_id = f"{device_code}_{description.key}"

    @property
    def native_value(self) -> Any:
        value = self._state.get(self.entity_description.state_field)
        if value is None:
            return None

        # Oven meat probe returns 65530 when probe is not inserted
        if self.entity_description.state_field == "currTempMeatProbe":
            try:
                if int(value) >= 65000:
                    return None
            except (TypeError, ValueError):
                pass

        # Cooking remaining = duration - elapsed (both in seconds)
        if self.entity_description.state_field == "currSeqDuration":
            elapsed = self._state.get("currSeqElapsedTime", 0)
            try:
                remaining = int(value) - int(elapsed)
                return max(0, remaining)
            except (TypeError, ValueError):
                pass

        return value
