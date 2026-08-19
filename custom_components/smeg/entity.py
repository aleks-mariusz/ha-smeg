"""Base entity class shared by all Smeg entity platforms."""
from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, smeg_device_name
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
        model_number = dev.get("modelNumber", "")
        name = smeg_device_name(model_number)

        # Commercial code for the model field (e.g. "SOP6606WS2PNR")
        from .const import SMEG_MODELS  # local import avoids circular at module level
        commercial_code = SMEG_MODELS.get(model_number, (model_number, ""))[0]

        mac = self._state.get("macAddress") or dev.get("physicalDeviceId", "")
        connections: set[tuple[str, str]] = set()
        if mac:
            connections.add((CONNECTION_NETWORK_MAC, mac.lower()))

        return DeviceInfo(
            identifiers={(DOMAIN, self._device_code)},
            name=name,
            manufacturer="Smeg",
            model=commercial_code or model_number,
            sw_version=dev.get("firmwareRev"),
            serial_number=dev.get("serialNumber"),
            connections=connections,
        )

    @property
    def available(self) -> bool:
        """Mark unavailable when the device reports cloud disconnected."""
        if not super().available:
            return False
        cloud = self._state.get("cloudConnected", "True")
        return str(cloud).lower() not in ("false", "0")
