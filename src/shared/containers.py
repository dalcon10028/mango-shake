import logging.config

from bitget.future_market_client import BitgetFutureMarketClient
from dependency_injector import containers, providers


class Container(containers.DeclarativeContainer):
    config = providers.Configuration(yaml_files=["config.yml"])

    logging = providers.Resource(
        logging.config.fileConfig,
        fname="logging.ini",
        disable_existing_loggers=False,
    )

    bitget_future_market_client = providers.Factory(
        BitgetFutureMarketClient,
        base_url=config.bitget.base_url,
        product_type=config.bitget.product_type,
    )
