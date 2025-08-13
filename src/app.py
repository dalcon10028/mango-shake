import asyncio
import logging

from dependency_injector.wiring import inject, Provide
from exchange.bitget.websocket_public_client import BitgetWebsocketClient
from shared.containers import Container

logger = logging.getLogger("main")


@inject
async def main(
    public_client: BitgetWebsocketClient = Provide[
        Container.bitget_future_websocket_public_client
    ],
):
    # Start connection in background
    conn_task = asyncio.create_task(public_client.connect())
    # Wait until connected before subscribing
    await public_client.wait_connected()
    # Keep running until interrupted
    try:
        await conn_task
    except asyncio.CancelledError:
        await public_client.close()


if __name__ == "__main__":
    container = Container()
    container.init_resources()
    container.wire(modules=[__name__])

    asyncio.run(main())
