from datetime import datetime
from bitget.client.signature_client import SignatureClient


class BitgetFutureTradeClient(SignatureClient):

    def __init__(
            self,
            base_url: str,
            access_key: str,
            secret_key: str,
            passphrase: str,
            locale: str = "ko-KR",
    ):
        super().__init__(base_url, access_key, secret_key, passphrase, locale=locale)

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

        return await self.get(path, params=params)
