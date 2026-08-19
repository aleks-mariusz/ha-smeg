"""Base entity class shared by all Smeg entity platforms."""
from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DEVICE_TYPE_NAMES, DOMAIN
from .coordinator import SmegCoordinator


class SmegEntity(CoordinatorEntity[SmegCoordinator]):
    """Base class for all Smeg entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: SmegCoordinator, device_code: str) -> None:
        super().__init__(coordinator)
        self._device_code = device_code

    @property
    def _device(self) -> dict[str, Any]:
        return self.coordinator.data.get(self._device_code, {})

    @property
    def _state(self) -> dict[str, Any]:
        return self._device.get("state", {})

    @property
    def device_info(self) -> DeviceInfo:
        dev = self._device
        type_id = dev.get("deviceTypeId", 0)
        type_name = DEVICE_TYPE_NAMES.get(type_id, "Appliance")
        model = dev.get("modelNumber", "Unknown")
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_code)},
            name=f"Smeg {type_name}",
            manufacturer="Smeg",
            model=model,
            sw_version=dev.get("firmwareRev"),
            serial_number=dev.get("serialNumber"),
        )

    @property
    def available(self) -> bool:
        """Mark unavailable when the device reports cloud disconnected."""
        if not super().available:
            return False
        cloud = self._state.get("cloudConnected", "True")
        return str(cloud).lower() not in ("false", "0")
