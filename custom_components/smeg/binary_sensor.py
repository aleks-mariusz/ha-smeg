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
    # All string values (case-insensitive) that mean "on/true".
    # Note: blast chiller returns integers for many boolean fields, so "1" must be included
    # where the oven might only use "ON"/"true".
    on_values: tuple[str, ...] = ("true", "on", "1")
    device_types: tuple[int, ...] = ()


BINARY_SENSOR_DESCRIPTIONS: tuple[SmegBinarySensorDescription, ...] = (
    SmegBinarySensorDescription(
        key="door",
        name="Door",
        state_field="doorState",
        on_values=("OPEN", "open"),
        device_class=BinarySensorDeviceClass.DOOR,
        # Blast chiller does NOT have a named doorState field in v1 state —
        # its door state is encoded in applState2_* bit arrays.
        # TODO v2 migration: decode bit arrays once ADF mapping is available.
        device_types=(DEVICE_TYPE_OVEN,),
    ),
    SmegBinarySensorDescription(
        key="cloud_connected",
        name="Cloud Connected",
        state_field="cloudConnected",
        # Oven returns JSON boolean true; blast chiller also returns boolean true.
        # str(True).lower() = "true" which matches.
        on_values=("true", "on", "1"),
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        device_types=(DEVICE_TYPE_OVEN, DEVICE_TYPE_BLAST_CHILLER),
    ),
    SmegBinarySensorDescription(
        key="remote_control",
        name="Remote Control Enabled",
        state_field="remoteControl",
        # Oven returns "ON" (string). Blast chiller returns integer 1.
        # Confirmed from live device query captures.
        # Not diagnostic — this is operationally important: most commands fail silently
        # when remote control is OFF. No entity_category → appears in main sensors section.
        on_values=("ON", "on", "true", "1"),
        device_types=(DEVICE_TYPE_OVEN, DEVICE_TYPE_BLAST_CHILLER),
    ),
    SmegBinarySensorDescription(
        key="oven_busy",
        name="Busy",
        state_field="ovenBusy",
        on_values=("oven busy",),
        device_types=(DEVICE_TYPE_OVEN,),
    ),
    # Renamed from "Meat Probe Inserted": the device reports whether the probe is
    # electrically connected, not whether food is being probed.
    # Oven: "meat probe not inserted as expected" string.
    # Blast chiller: integer 0 (not connected) / 1 (connected).
    SmegBinarySensorDescription(
        key="meat_probe",
        name="Meat Probe Connected",
        state_field="meatProbeInserted",
        on_values=("meat probe inserted", "1", "true"),
        device_types=(DEVICE_TYPE_OVEN, DEVICE_TYPE_BLAST_CHILLER),
    ),
    SmegBinarySensorDescription(
        key="child_lock",
        name="Child Lock Active",
        state_field="childlock",
        on_values=("ON", "on", "true", "1"),
        device_class=BinarySensorDeviceClass.LOCK,
        # Blast chiller: no named childlock field in v1 state (encoded in bit arrays).
        # Oven: if child lock is physically active on the oven display, the oven firmware
        # will ALSO block remote commands — the childlockFeature command may be accepted
        # (202) but silently ignored until child lock is disabled on the physical display.
        device_types=(DEVICE_TYPE_OVEN,),
    ),
    # True when the appliance is reporting an active error (failureCode != 0).
    # Oven only — blast chiller uses separate alarmStatus_* fields.
    SmegBinarySensorDescription(
        key="error_active",
        name="Error Active",
        state_field="failureCode",
        # on = any non-zero value (error present)
        on_values=(),   # handled with custom logic in is_on
        entity_category=EntityCategory.DIAGNOSTIC,
        device_types=(DEVICE_TYPE_OVEN,),
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

        # Error Active: True when failureCode is a non-zero integer
        if self.entity_description.key == "error_active":
            try:
                return int(value) != 0
            except (TypeError, ValueError):
                return None

        v = str(value).lower()
        return v in {s.lower() for s in self.entity_description.on_values}
