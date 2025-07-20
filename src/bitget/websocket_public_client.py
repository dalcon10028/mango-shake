import asyncio
import json
import logging

from websockets import ConnectionClosed, ConnectionClosedError
from websockets.asyncio.client import connect
from websockets.legacy.exceptions import InvalidStatusCode

logger = logging.getLogger("websockets")
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())


async def _heartbeat(ws):
    while True:
        await ws.send("ping")
        await asyncio.sleep(30)


class BitgetWebsocketPublicClient:

    def __init__(self, url: str, reconnect_max_delay: int = 60):
        self._ws = connect(url, ping_interval=None,ping_timeout=None)
        self._reconnect_max_delay = reconnect_max_delay

    async def subscribe_candlestick(self):
        reconnect_delay = 1
        async for ws in self._ws:
            try:
                msg = {
                    "op": "subscribe",
                    "args": [
                        {
                            "instType": "USDT-FUTURES",
                            "channel": "candle1m",
                            "instId": "BTCUSDT"
                        }
                    ]
                }
                await ws.send(json.dumps(msg))

                ack = json.loads(await ws.recv())
                if ack.get("event") != "subscribe":
                    raise RuntimeError(f"Subscribe failed: {ack}")

                asyncio.create_task(_heartbeat(ws))

                async for message in ws:
                    logger.debug(message)
            except (ConnectionClosedError, InvalidStatusCode, OSError) as e:
                logger.warning(f"Connection lost: {e}. Reconnecting in {reconnect_delay}s...")
                await asyncio.sleep(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 2, self._reconnect_max_delay)

            except Exception as e:
                logger.exception(f"Unexpected error: {e}")
                await asyncio.sleep(5)