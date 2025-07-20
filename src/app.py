import asyncio
import logging

from bitget.future_market_client import BitgetFutureMarketClient
from dependency_injector.wiring import inject, Provide
from shared.containers import Container

logger = logging.getLogger("main")


@inject
async def main(
    client: BitgetFutureMarketClient = Provide[Container.bitget_future_market_client],
):

    logger.info("hello")
    async with client:
        await client.get_contract_config("BTCUSDT")
        logger.debug("done")


if __name__ == "__main__":
    container = Container()
    container.init_resources()
    container.wire(modules=[__name__])

    asyncio.run(main())
