"""Binary sensor entities for Smeg appliances."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DEVICE_TYPE_BLAST_CHILLER, DEVICE_TYPE_OVEN, DOMAIN
from .coordinator import SmegCoordinator
from .entity import SmegEntity


@dataclass(frozen=True, kw_only=True)
class SmegBinarySensorDescription(BinarySensorEntityDescription):
    state_field: str = ""
    on_value: str = "true"
    device_types: tuple[int, ...] = ()


BINARY_SENSOR_DESCRIPTIONS: tuple[SmegBinarySensorDescription, ...] = (
    SmegBinarySensorDescription(
        key="door",
        name="Door",
        state_field="doorState",
        on_value="OPEN",
        device_class=BinarySensorDeviceClass.DOOR,
        device_types=(DEVICE_TYPE_OVEN, DEVICE_TYPE_BLAST_CHILLER),
    ),
    SmegBinarySensorDescription(
        key="cloud_connected",
        name="Cloud Connected",
        state_field="cloudConnected",
        on_value="True",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        device_types=(DEVICE_TYPE_OVEN, DEVICE_TYPE_BLAST_CHILLER),
    ),
    SmegBinarySensorDescription(
        key="remote_control",
        name="Remote Control Enabled",
        state_field="remoteControl",
        on_value="ON",
        # Diagnostic but enabled — user needs to know if this is OFF when commands fail
        entity_category=EntityCategory.DIAGNOSTIC,
        device_types=(DEVICE_TYPE_OVEN, DEVICE_TYPE_BLAST_CHILLER),
    ),
    SmegBinarySensorDescription(
        key="oven_busy",
        name="Busy",
        state_field="ovenBusy",
        on_value="oven busy",
        device_types=(DEVICE_TYPE_OVEN,),
    ),
    SmegBinarySensorDescription(
        key="meat_probe",
        name="Meat Probe Inserted",
        state_field="meatProbeInserted",
        on_value="meat probe inserted",
        device_types=(DEVICE_TYPE_OVEN, DEVICE_TYPE_BLAST_CHILLER),
    ),
    SmegBinarySensorDescription(
        key="child_lock",
        name="Child Lock Active",
        state_field="childlock",
        on_value="ON",
        device_class=BinarySensorDeviceClass.LOCK,
        device_types=(DEVICE_TYPE_OVEN, DEVICE_TYPE_BLAST_CHILLER),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: SmegCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SmegBinarySensorEntity] = []

    for device_code, device in coordinator.data.items():
        type_id = device.get("deviceTypeId", 0)
        for desc in BINARY_SENSOR_DESCRIPTIONS:
            if type_id in desc.device_types:
                entities.append(SmegBinarySensorEntity(coordinator, device_code, desc))

    async_add_entities(entities)


class SmegBinarySensorEntity(SmegEntity, BinarySensorEntity):
    """A binary sensor entity for a Smeg state field."""

    entity_description: SmegBinarySensorDescription

    def __init__(
        self,
        coordinator: SmegCoordinator,
        device_code: str,
        description: SmegBinarySensorDescription,
    ) -> None:
        super().__init__(coordinator, device_code)
        self.entity_description = description
        self._attr_unique_id = f"{device_code}_{description.key}"

    @property
    def is_on(self) -> bool | None:
        value = self._state.get(self.entity_description.state_field)
        if value is None:
            return None
        return str(value).lower() == self.entity_description.on_value.lower()
