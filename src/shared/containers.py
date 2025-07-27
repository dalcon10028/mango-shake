import logging.config

from reactivex import Subject
from bitget.future_market_client import BitgetFutureMarketClient
from dependency_injector import containers, providers

from bitget.stream_manager import BitgetStreamManager
from bitget.websocket_public_client import BitgetWebsocketClient


class Container(containers.DeclarativeContainer):
    config = providers.Configuration(yaml_files=["config.yml"])

    logging = providers.Resource(
        logging.config.fileConfig,
        fname="logging.ini",
        disable_existing_loggers=False,
    )

    bitget_stream_manager = providers.Resource(
        BitgetStreamManager,
        strategies=config.strategy,
    )


    bitget_future_market_client = providers.Singleton(
        BitgetFutureMarketClient,
        base_url=config.bitget.base_url,
        product_type=config.bitget.product_type,
    )

    bitget_future_websocket_public_client = providers.Singleton(
        BitgetWebsocketClient,
        url=config.bitget.websocket_public_url,
        stream_manager=bitget_stream_manager,
    )