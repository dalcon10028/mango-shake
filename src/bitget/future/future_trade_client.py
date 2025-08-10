from datetime import datetime

from bitget.utils.signature import generate_signature
from shared.tracing_client_session import TracingClientSession
import time

class BitgetFutureTradeClient:

    def __init__(self, base_url: str, access_key: str, secret_key: str, passphrase: str):
        self._access_key = access_key
        self._secret_key = secret_key
        self._passphrase = passphrase
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "ACCESS-KEY": access_key,
            "locale": "ko-KR",
        }

        self._client = TracingClientSession(base_url=base_url, headers=headers)

    async def __aenter__(self) -> "BitgetFutureTradeClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self._client.close()

    async def get_history_orders(
        self,
        product_type: str,
        order_id: str = None,
        client_oid: str = None,
        symbol: str = None,
        id_less_than: str = None,
        order_source: str = None,
        start_time: datetime = None,
        end_time: datetime = None,
        limit: int = 100,
    ):
        """
        Fetch historical orders (up to 90 days) from Bitget.
        """
        path = "/api/v2/mix/order/orders-history"
        # assemble query params
        params = {"productType": product_type}
        for key, value in [
            ("orderId", order_id),
            ("clientOid", client_oid),
            ("symbol", symbol),
            ("idLessThan", id_less_than),
            ("orderSource", order_source),
            ("startTime", str(int(start_time.timestamp() * 1000)) if start_time else None),
            ("endTime", str(int(end_time.timestamp() * 1000)) if end_time else None),
            ("limit", limit)
        ]:
            if value is not None:
                params[key] = value

        # signature headers
        timestamp = str(int(time.time() * 1000))

        # build query string for signing
        query_string = "&".join(f"{k}={v}" for k, v in params.items())

        sign = generate_signature(self._secret_key, timestamp, "GET", path, query_string, "")

        headers = {
            "ACCESS-KEY": self._access_key,
            "ACCESS-SIGN": sign,
            "ACCESS-TIMESTAMP": timestamp,
            "ACCESS-PASSPHRASE": self._passphrase,
            "Content-Type": "application/json",
        }
        async with self._client.get(path, params=params, headers=headers) as resp:
            resp.raise_for_status()
            return await resp.json()
