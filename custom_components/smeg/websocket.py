"""Raw STOMP over WebSocket client for real-time Smeg device state pushes.

Charles proxy captures confirm the app connects to:
  wss://ws.prod-platform.smegconnect.com/register/websocket

This is Spring's raw WebSocket STOMP endpoint — NOT the SockJS transport
path (register/{server}/{session}/websocket). No SockJS framing is used.
STOMP frames are sent and received as plain WebSocket text messages.
"""
from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Coroutine
from typing import Any

import aiohttp

from .auth import SmegAuth

_LOGGER = logging.getLogger(__name__)

WS_URL = "wss://ws.prod-platform.smegconnect.com/register/websocket"
_CONNECT_TIMEOUT = 20
_HEARTBEAT_INTERVAL = 25


# ---------------------------------------------------------------------------
# STOMP frame helpers
# ---------------------------------------------------------------------------

def _stomp_frame(command: str, headers: dict[str, str], body: str = "") -> str:
    """Build a STOMP 1.1 frame string."""
    lines = [command]
    for k, v in headers.items():
        lines.append(f"{k}:{v}")
    lines.append("")           # blank line separates headers from body
    lines.append(body + "\x00")
    return "\n".join(lines)


def _parse_stomp(text: str) -> dict[str, Any]:
    """Parse a STOMP frame string into {command, headers, body}."""
    text = text.rstrip("\x00").strip("\n")
    header_part, _, body = text.partition("\n\n")
    lines = header_part.split("\n")
    command = lines[0].strip()
    headers: dict[str, str] = {}
    for line in lines[1:]:
        if ":" in line:
            k, _, v = line.partition(":")
            headers[k.strip()] = v.strip()
    return {"command": command, "headers": headers, "body": body}


# ---------------------------------------------------------------------------
# Callback types
# ---------------------------------------------------------------------------

DisconnectCallback = Callable[[None], Coroutine[Any, Any, None]]
MessageCallback = Callable[[dict[str, Any]], Coroutine[Any, Any, None]]


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class SmegWebSocket:
    """Persistent raw STOMP WebSocket connection to the Smeg cloud."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        auth: SmegAuth,
        on_disconnect: DisconnectCallback,
        on_message: MessageCallback,
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
        """Open WebSocket, perform STOMP handshake, subscribe. Raises on failure."""
        self._running = True
        token = await self._auth.get_access_token()

        _LOGGER.debug("Connecting raw STOMP WebSocket: %s", WS_URL)

        async with asyncio.timeout(_CONNECT_TIMEOUT):
            self._ws = await self._session.ws_connect(WS_URL, heartbeat=None)

            # Send STOMP CONNECT
            connect = _stomp_frame(
                "CONNECT",
                {
                    "accept-version": "1.1,1.0",
                    "heart-beat": "0,0",
                    "Authorization": f"Bearer {token}",
                    "x-tenant": "smegcons",
                },
            )
            await self._ws.send_str(connect)

            # Receive CONNECTED (ignore leading heartbeat newlines)
            connected = await self._recv_stomp_frame()
            if connected is None:
                raise ConnectionError("WebSocket closed before CONNECTED frame")
            if connected["command"] == "ERROR":
                raise ConnectionError(
                    f"STOMP CONNECT rejected: {connected['headers'].get('message', connected['body'])}"
                )
            if connected["command"] != "CONNECTED":
                raise ConnectionError(
                    f"Expected CONNECTED, got {connected['command']!r}"
                )

            # Send STOMP SUBSCRIBE
            sub = _stomp_frame(
                "SUBSCRIBE",
                {
                    "destination": f"/status/change/{self._auth.iot_user_code}",
                    "id": "sub-0",
                    "ack": "auto",
                },
            )
            await self._ws.send_str(sub)

        self._listen_task = asyncio.ensure_future(self._listen())
        self._heartbeat_task = asyncio.ensure_future(self._heartbeat())
        _LOGGER.info("Smeg STOMP WebSocket connected and subscribed")

    async def async_disconnect(self) -> None:
        """Close the WebSocket cleanly. Does NOT trigger the disconnect callback."""
        self._running = False
        for task in (self._heartbeat_task, self._listen_task):
            if task:
                task.cancel()
        self._heartbeat_task = None
        self._listen_task = None
        if self._ws and not self._ws.closed:
            try:
                # Send STOMP DISCONNECT so the server cleans up the session immediately
                await self._ws.send_str(_stomp_frame("DISCONNECT", {"receipt": "close"}))
            except Exception:
                pass
            try:
                await self._ws.close()
            except Exception:
                pass
        self._ws = None

    # -----------------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------------

    async def _recv_stomp_frame(self) -> dict[str, Any] | None:
        """Receive the next non-heartbeat WebSocket message and parse as STOMP."""
        while True:
            msg = await self._ws.receive()
            if msg.type == aiohttp.WSMsgType.TEXT:
                text = msg.data.strip()
                if not text:        # heartbeat — skip
                    continue
                return _parse_stomp(text)
            if msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                return None

    async def _listen(self) -> None:
        try:
            while self._running:
                frame = await self._recv_stomp_frame()
                if frame is None:
                    _LOGGER.debug("WebSocket closed during listen")
                    break
                await self._dispatch(frame)
        except asyncio.CancelledError:
            return
        except Exception:
            _LOGGER.debug("WebSocket listener error", exc_info=True)
        finally:
            if self._running:
                self._running = False
                await self._on_disconnect(None)

    async def _dispatch(self, frame: dict[str, Any]) -> None:
        cmd = frame["command"]
        if cmd == "MESSAGE":
            try:
                import json
                payload = json.loads(frame["body"])
                await self._on_message(payload)
            except Exception:
                _LOGGER.debug("Could not parse MESSAGE body: %s", frame["body"][:100])
        elif cmd == "ERROR":
            msg = frame["headers"].get("message", frame["body"][:100])
            _LOGGER.warning("STOMP ERROR from server: %s — will reconnect", msg)
            if self._running:
                self._running = False
                await self._on_disconnect(None)
        elif cmd == "RECEIPT":
            pass    # not requested, ignore
        else:
            _LOGGER.debug("Unhandled STOMP frame: %s", cmd)

    async def _heartbeat(self) -> None:
        """Send periodic STOMP heartbeat newlines to keep the connection alive."""
        try:
            while self._running:
                await asyncio.sleep(_HEARTBEAT_INTERVAL)
                if self._ws and not self._ws.closed and self._running:
                    await self._ws.send_str("\n")
        except asyncio.CancelledError:
            pass
        except Exception:
            _LOGGER.debug("Heartbeat task ended", exc_info=True)
