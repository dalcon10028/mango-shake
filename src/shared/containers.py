import logging.config

from exchange.bitget.future.future_account_client import BitgetFutureAccountClient
from exchange.bitget.future.future_market_client import BitgetFutureMarketClient
from dependency_injector import containers, providers

from exchange.bitget.future.future_position_client import BitgetFuturePositionClient
from exchange.bitget.future.future_trade_client import BitgetFutureTradeClient
from exchange.bitget.stream_manager import BitgetStreamManager
from exchange.bitget.websocket_public_client import BitgetWebsocketClient
from exchange.kiwoom.rest_client import KiwoomRestClient


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

    bitget_future_trade_client = providers.Singleton(
        BitgetFutureTradeClient,
        base_url=config.bitget.base_url,
        access_key=config.wallet.bitget.api_key,
        secret_key=config.wallet.bitget.api_secret,
        passphrase=config.wallet.bitget.passphrase,
    )

    bitget_future_account_client = providers.Singleton(
        BitgetFutureAccountClient,
        base_url=config.bitget.base_url,
        access_key=config.wallet.bitget.api_key,
        secret_key=config.wallet.bitget.api_secret,
        passphrase=config.wallet.bitget.passphrase,
    )

    bitget_future_position_client = providers.Singleton(
        BitgetFuturePositionClient,
        base_url=config.bitget.base_url,
        access_key=config.wallet.bitget.api_key,
        secret_key=config.wallet.bitget.api_secret,
        passphrase=config.wallet.bitget.passphrase,
    )

    bitget_future_websocket_public_client = providers.Singleton(
        BitgetWebsocketClient,
        url=config.bitget.websocket_public_url,
        stream_manager=bitget_stream_manager,
    )

    kiwoom_rest_client = providers.Singleton(
        KiwoomRestClient,
        base_url=config.kiwoom.base_url,
        app_key=config.kiwoom.app_key,
        app_secret=config.kiwoom.secret_key,
    )