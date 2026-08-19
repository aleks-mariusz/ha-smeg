"""DataUpdateCoordinator for Smeg — one per config entry (account).

State delivery:
  Primary:  STOMP WebSocket push (real-time, ~1-5s latency)
  Fallback: REST polling every 30s when WebSocket is disconnected

self.data layout:
  {
    "<deviceCode>": {
      "deviceCode": "...",
      "deviceTypeId": 7,
      "modelNumber": "...",
      "serialNumber": "...",
      "firmwareRev": "...",
      "deviceTypeName": "OVEN",
      "state": { <200+ status fields> },
      "availableCommands": [...],
    },
    ...
  }
"""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import SmegApi, SmegApiError
from .auth import SmegAuth
from .const import WS_RECONNECT_MAX_DELAY
from .websocket import SmegWebSocket

_LOGGER = logging.getLogger(__name__)
_POLL_INTERVAL = timedelta(seconds=30)

# Minimum seconds between reconnect attempts — prevents server-ERROR storm
_RECONNECT_COOLDOWN = 5


class SmegCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    """Single coordinator for one Smeg cloud account."""

    def __init__(
        self,
        hass: HomeAssistant,
        auth: SmegAuth,
        api: SmegApi,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="smeg",
            update_interval=_POLL_INTERVAL,
        )
        self.auth = auth
        self.api = api
        self._ws: SmegWebSocket | None = None
        self._ws_connected = False
        self._reconnect_task: asyncio.Task | None = None
        self._reconnecting = False          # guard: only one reconnect loop at a time
        self.data: dict[str, dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # Setup / teardown
    # ------------------------------------------------------------------

    async def async_setup(self) -> None:
        """Fetch device list + initial state, then open WebSocket."""
        await self._fetch_all_devices()
        await self._start_websocket()

    async def async_stop(self) -> None:
        """Called when the config entry is unloaded."""
        self._reconnecting = True           # prevent any new reconnects
        if self._reconnect_task and not self._reconnect_task.done():
            self._reconnect_task.cancel()
            try:
                await self._reconnect_task
            except asyncio.CancelledError:
                pass
        if self._ws:
            await self._ws.async_disconnect()

    # ------------------------------------------------------------------
    # DataUpdateCoordinator override (fallback polling)
    # ------------------------------------------------------------------

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        """Called on the 30s interval; only polls when WebSocket is down."""
        if self._ws_connected:
            return self.data

        _LOGGER.debug("WebSocket not connected — polling REST API")
        for code in list(self.data):
            try:
                info = await self.api.get_device_info(code)
                self.data[code]["state"] = (
                    info.get("highLevelDeviceStatus", {}).get("status", {})
                )
            except SmegApiError as err:
                raise UpdateFailed(f"Failed to poll {code}: {err}") from err
        return self.data

    # ------------------------------------------------------------------
    # WebSocket management
    # ------------------------------------------------------------------

    async def _start_websocket(self) -> None:
        """Create and connect a fresh SmegWebSocket. Sets _ws_connected."""
        if self._ws:
            await self._ws.async_disconnect()

        session = async_get_clientsession(self.hass)
        self._ws = SmegWebSocket(
            session,
            self.auth,
            on_disconnect=self._on_ws_disconnect,
            on_message=self._on_ws_message,
        )
        try:
            await self._ws.async_connect()
            self._ws_connected = True
        except Exception:
            _LOGGER.warning(
                "Failed to connect WebSocket — will rely on polling", exc_info=True
            )
            self._ws_connected = False

    async def _on_ws_disconnect(self, _payload: None) -> None:
        """Called by SmegWebSocket when the connection drops."""
        self._ws_connected = False
        if self._reconnecting:
            return
        _LOGGER.warning("Smeg WebSocket disconnected — scheduling reconnect")
        self._schedule_reconnect()

    async def _on_ws_message(self, payload: dict[str, Any]) -> None:
        """Called by SmegWebSocket on each inbound state push."""
        device_code = payload.get("deviceCode")
        status = payload.get("status")
        if not device_code or not status:
            return
        if device_code not in self.data:
            _LOGGER.debug("State push for unknown device %s — ignoring", device_code)
            return

        self.data[device_code]["state"] = status
        self.async_set_updated_data(self.data)

    def _schedule_reconnect(self) -> None:
        """Schedule _reconnect_loop as a background task — only one at a time."""
        if self._reconnecting:
            return
        if self._reconnect_task and not self._reconnect_task.done():
            return                          # already running
        self._reconnect_task = self.hass.async_create_task(
            self._reconnect_loop(), name="smeg_ws_reconnect"
        )

    async def _reconnect_loop(self) -> None:
        """Exponential backoff reconnect. Re-fetches state on success."""
        self._reconnecting = True
        delay = _RECONNECT_COOLDOWN  # always start at 5s minimum
        try:
            while True:
                _LOGGER.debug("WebSocket reconnect attempt in %ss", delay)
                await asyncio.sleep(delay)
                try:
                    await self._start_websocket()
                    await self._fetch_all_devices()
                    self.async_set_updated_data(self.data)
                    _LOGGER.info("Smeg WebSocket reconnected successfully")
                    return
                except asyncio.CancelledError:
                    raise
                except Exception:
                    _LOGGER.debug("Reconnect attempt failed", exc_info=True)
                    delay = min(delay * 2, WS_RECONNECT_MAX_DELAY)
        except asyncio.CancelledError:
            pass
        finally:
            self._reconnecting = False

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _fetch_all_devices(self) -> None:
        """Populate self.data with device list + current state."""
        devices_raw = await self.api.get_devices()
        for dev in devices_raw:
            code = dev["deviceCode"]
            try:
                info = await self.api.get_device_info(code)
            except SmegApiError:
                _LOGGER.warning("Could not fetch info for device %s", code)
                info = {}

            existing_state = self.data.get(code, {}).get("state", {})
            self.data[code] = {
                **dev,
                "state": info.get("highLevelDeviceStatus", {}).get(
                    "status", existing_state
                ),
                "availableCommands": info.get("availableCommands", []),
            }
