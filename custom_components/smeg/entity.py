"""Base entity class shared by all Smeg entity platforms."""
from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, SMEG_MODEL_NAMES
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
        # Use the commercial product code (e.g. "SOP6606WS2PNR") if known;
        # fall back to the internal model number from the API.
        commercial_code = SMEG_MODEL_NAMES.get(model_number, model_number or "Unknown")

        # MAC address from state (formatted as reported by firmware)
        mac = self._state.get("macAddress") or dev.get("physicalDeviceId", "")

        connections: set[tuple[str, str]] = set()
        if mac:
            connections.add((CONNECTION_NETWORK_MAC, mac.lower()))

        return DeviceInfo(
            identifiers={(DOMAIN, self._device_code)},
            # Name uses commercial code so two ovens with different models are distinct
            name=f"Smeg {commercial_code}",
            manufacturer="Smeg",
            model=commercial_code,
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
