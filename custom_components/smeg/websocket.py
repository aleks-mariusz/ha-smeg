"""STOMP over SockJS WebSocket client for real-time Smeg device state pushes.

Protocol stack:
  aiohttp WebSocket (TLS transport)
    └── SockJS framing  (o / h / a[...] / c[...])
          └── STOMP 1.1  (CONNECT → CONNECTED → SUBSCRIBE → MESSAGE)

The SockJS WebSocket URL pattern is:
  wss://ws.prod-platform.smegconnect.com/register/{server_id}/{session_id}/websocket
where server_id is a random 3-digit string and session_id is 8 random chars.

Client→server SockJS frames are bare JSON arrays: ["stomp frame string"]
Server→client SockJS frames are prefixed:
  o          — session open
  h          — server heartbeat (no response required)
  a["..."]   — data array
  c[code,"reason"] — close
"""
from __future__ import annotations

import asyncio
import json
import logging
import random
import string
from collections.abc import Callable, Coroutine
from typing import Any

import aiohttp

from .auth import SmegAuth
from .const import WS_BASE

_LOGGER = logging.getLogger(__name__)

_HEARTBEAT_INTERVAL = 25
_CONNECT_TIMEOUT = 20


def _server_id() -> str:
    return str(random.randint(0, 999)).zfill(3)


def _session_id() -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=8))


def _stomp_frame(command: str, headers: dict[str, str], body: str = "") -> str:
    lines = [command]
    for k, v in headers.items():
        lines.append(f"{k}:{v}")
    lines.append("")
    lines.append(body + "\x00")
    return "\n".join(lines)


def _parse_stomp(text: str) -> dict[str, Any]:
    text = text.rstrip("\x00")
    header_part, _, body = text.partition("\n\n")
    lines = header_part.split("\n")
    command = lines[0]
    headers: dict[str, str] = {}
    for line in lines[1:]:
        if ":" in line:
            k, _, v = line.partition(":")
            headers[k.strip()] = v.strip()
    return {"command": command, "headers": headers, "body": body}


def _extract_sockjs_frames(data: str) -> list[str]:
    if not data.startswith("a"):
        return []
    try:
        return json.loads(data[1:])
    except json.JSONDecodeError:
        _LOGGER.debug("Failed to parse SockJS frame: %s", data[:200])
        return []


StateUpdateCallback = Callable[[dict[str, Any] | None], Coroutine[Any, Any, None]]


class SmegWebSocket:
    """Maintains a persistent STOMP/SockJS WebSocket connection."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        auth: SmegAuth,
        on_disconnect: StateUpdateCallback,
        on_message: StateUpdateCallback,
    ) -> None:
        self._session = session
        self._auth = auth
        self._on_disconnect = on_disconnect
        self._on_message = on_message
        self._ws: aiohttp.ClientWebSocketResponse | None = None
        self._running = False
        self._listen_task: asyncio.Task | None = None
        self._heartbeat_task: asyncio.Task | None = None

    async def async_connect(self) -> None:
        """Connect, STOMP handshake, subscribe, start listener. Raises on failure."""
        self._running = True
        url = f"{WS_BASE}/{_server_id()}/{_session_id()}/websocket"
        _LOGGER.debug("Connecting STOMP WebSocket: %s", url)

        token = await self._auth.get_access_token()

        async with asyncio.timeout(_CONNECT_TIMEOUT):
            self._ws = await self._session.ws_connect(url, heartbeat=None)

            # SockJS open frame
            msg = await self._ws.receive()
            if msg.type != aiohttp.WSMsgType.TEXT or msg.data != "o":
                raise ConnectionError(
                    f"Expected SockJS 'o' open frame, got: {msg.data!r}"
                )

            # STOMP CONNECT
            connect = _stomp_frame(
                "CONNECT",
                {
                    "accept-version": "1.1,1.0",
                    "heart-beat": "0,0",
                    "Authorization": f"Bearer {token}",
                    "x-tenant": "smegcons",
                },
            )
            await self._ws.send_str(json.dumps([connect]))

            # Wait for CONNECTED
            msg = await self._ws.receive()
            if msg.type != aiohttp.WSMsgType.TEXT:
                raise ConnectionError("No response to STOMP CONNECT")
            frames = _extract_sockjs_frames(msg.data)
            if not frames:
                raise ConnectionError("Empty SockJS frame during handshake")
            parsed = _parse_stomp(frames[0])
            if parsed["command"] == "ERROR":
                raise ConnectionError(
                    f"STOMP CONNECT rejected: {parsed['headers'].get('message', parsed['body'])}"
                )
            if parsed["command"] != "CONNECTED":
                raise ConnectionError(
                    f"Expected CONNECTED, got {parsed['command']}"
                )

            # STOMP SUBSCRIBE
            sub = _stomp_frame(
                "SUBSCRIBE",
                {
                    "destination": f"/status/change/{self._auth.iot_user_code}",
                    "id": "sub-0",
                    "ack": "auto",
                },
            )
            await self._ws.send_str(json.dumps([sub]))

        self._listen_task = asyncio.ensure_future(self._listen())
        self._heartbeat_task = asyncio.ensure_future(self._heartbeat())
        _LOGGER.info("Smeg STOMP WebSocket connected and subscribed")

    async def async_disconnect(self) -> None:
        """Cleanly close the WebSocket. Does NOT trigger the disconnect callback."""
        self._running = False
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            self._heartbeat_task = None
        if self._listen_task:
            self._listen_task.cancel()
            self._listen_task = None
        if self._ws and not self._ws.closed:
            try:
                await self._ws.close()
            except Exception:
                pass
        self._ws = None

    async def _listen(self) -> None:
        try:
            async for msg in self._ws:
                if not self._running:
                    break
                if msg.type == aiohttp.WSMsgType.TEXT:
                    await self._handle_frame(msg.data)
                elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                    _LOGGER.debug("WebSocket closed/error msg: %s", msg)
                    break
        except asyncio.CancelledError:
            return
        except Exception:
            _LOGGER.debug("WebSocket listener error", exc_info=True)
        finally:
            if self._running:
                self._running = False
                await self._on_disconnect(None)

    async def _handle_frame(self, data: str) -> None:
        if data in ("o", "h"):
            return
        if data.startswith("c"):
            _LOGGER.debug("SockJS close frame: %s", data)
            return
        if not data.startswith("a"):
            return

        for frame_str in _extract_sockjs_frames(data):
            parsed = _parse_stomp(frame_str)
            if parsed["command"] == "MESSAGE":
                try:
                    payload = json.loads(parsed["body"])
                    await self._on_message(payload)
                except json.JSONDecodeError:
                    _LOGGER.debug("Non-JSON STOMP body: %s", parsed["body"][:100])
            elif parsed["command"] == "ERROR":
                msg = parsed["headers"].get("message", "unknown")
                _LOGGER.warning(
                    "STOMP ERROR from server: %s — will reconnect", msg
                )
                # Treat server ERROR as a disconnect; stop and let coordinator reconnect
                if self._running:
                    self._running = False
                    await self._on_disconnect(None)
                return

    async def _heartbeat(self) -> None:
        try:
            while self._running:
                await asyncio.sleep(_HEARTBEAT_INTERVAL)
                if self._ws and not self._ws.closed and self._running:
                    await self._ws.send_str(json.dumps(["\n"]))
        except asyncio.CancelledError:
            pass
        except Exception:
            _LOGGER.debug("Heartbeat ended", exc_info=True)
