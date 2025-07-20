import asyncio
import logging

from bitget.future_market_client import BitgetFutureMarketClient
from dependency_injector.wiring import inject, Provide

from bitget.websocket_public_client import BitgetWebsocketPublicClient
from shared.containers import Container

logger = logging.getLogger("main")


@inject
async def main(
    public_client: BitgetWebsocketPublicClient = Provide[
        Container.bitget_future_websocket_public_client
    ],
):
    await public_client.subscribe_candlestick()


if __name__ == "__main__":
    container = Container()
    container.init_resources()
    container.wire(modules=[__name__])

    asyncio.run(main())
