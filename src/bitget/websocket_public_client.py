import asyncio
import json
import logging
from typing import List, Optional, Set

from websockets import ConnectionClosed
from websockets.asyncio.client import connect

from bitget.dto.websocket import BaseWsReq, SubscribeReq
from bitget.stream_manager import BitgetStreamManager

logger = logging.getLogger("websockets")
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())

WS_PING = 'ping'
WS_OP_LOGIN = 'login'
WS_OP_SUBSCRIBE = "subscribe"
WS_OP_UNSUBSCRIBE = "unsubscribe"


async def _heartbeat(ws):
    while True:
        await ws.send("ping")
        await asyncio.sleep(30)


class BitgetWebsocketClient:
    """
    Async WebSocket client for Bitget with automatic reconnect,
    heartbeat, and subscription management.
    """

    def __init__(
        self,
        url: str,
        stream_manager: BitgetStreamManager,
        reconnect_delay: int = 1,
        max_reconnect_delay: int = 60,
        heartbeat_interval: int = 30,
    ):
        self._stream_manager = stream_manager

        self._url = url
        self._reconnect_delay = reconnect_delay
        self._max_reconnect_delay = max_reconnect_delay
        self._heartbeat_interval = heartbeat_interval

        self._ws: Optional[asyncio.StreamReader] = None
        self._channels: Set[SubscribeReq] = set(stream_manager.channels)
        self._stop_event = asyncio.Event()
        self._connected_event = asyncio.Event()

    async def connect(self):
        delay = self._reconnect_delay
        while not self._stop_event.is_set():
            try:
                logger.info(f"Connecting to {self._url}")
                async with connect(self._url, ping_interval=None, ping_timeout=None) as ws:
                    self._ws = ws
                    self._connected_event.set()
                    delay = self._reconnect_delay
                    hb_task = asyncio.create_task(self._heartbeat())
                    await self._resubscribe_all()
                    await self._receiver_loop()
            except ConnectionClosed as e:
                logger.warning(f"Connection closed: {e}. Reconnect in {delay}s...")
            except Exception as e:
                logger.exception(f"Error: {e}. Reconnect in {delay}s...")
            finally:
                self._connected_event.clear()
            await asyncio.sleep(delay)
            delay = min(delay * 2, self._max_reconnect_delay)

    async def wait_connected(self):
        await self._connected_event.wait()

    async def _receiver_loop(self):
        assert self._ws is not None
        async for raw in self._ws:
            try:
                if "pong" == raw:
                    continue
                msg = json.loads(raw)
                logger.debug(f"Received: {msg}")
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON: {raw}")

    async def _heartbeat(self):
        assert self._ws is not None
        while True:
            try:
                await self._ws.send(WS_PING)
                logger.debug("Ping sent")
            except Exception as e:
                logger.warning(f"Heartbeat error: {e}")
                return
            await asyncio.sleep(self._heartbeat_interval)

    async def _send(self, op: str, args: List[dict]):
        if not self._ws:
            logger.error("Not connected, cannot send")
            return
        payload = BaseWsReq(op, args)
        msg = json.dumps(payload, default=lambda o: o.__dict__)
        logger.debug(f"Sending: {msg}")
        await self._ws.send(msg)

    async def subscribe(self, channels: List[SubscribeReq]):
        new = [ch for ch in channels if ch not in self._channels]
        if not new:
            logger.info("No new subscriptions")
            return
        self._channels.update(new)
        await self._send(WS_OP_SUBSCRIBE, [vars(ch) for ch in new])

    async def unsubscribe(self, channels: List[SubscribeReq]):
        rem = [ch for ch in channels if ch in self._channels]
        if not rem:
            logger.info("No subscriptions to remove")
            return
        for ch in rem:
            self._channels.remove(ch)
        await self._send(WS_OP_UNSUBSCRIBE, [vars(ch) for ch in rem])

    async def _resubscribe_all(self):
        if self._channels:
            logger.info(f"Resubscribing: {self._channels}")
            await self._send(WS_OP_SUBSCRIBE, [vars(ch) for ch in self._channels])

    async def close(self):
        self._stop_event.set()
        if self._ws:
            await self._ws.close()
