from datetime import datetime
from decimal import Decimal
from typing import Optional


from exchange.bitget.client.signature_client import SignatureClient


class BitgetFutureTradeClient(SignatureClient):

    def __init__(
            self,
            base_url: str,
            access_key: str,
            secret_key: str,
            passphrase: str,
    ):
        super().__init__(base_url, access_key, secret_key, passphrase)

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

    async def place_order(self,
        symbol: str,
        product_type: str,
        size: Decimal,
        side: str,
        order_type: str = 'limit',
        price: Optional[Decimal] = None,
    ):
        """
        Place a new order on Bitget.
        """
        path = "/api/v2/mix/order/place-order"
        body = {
            "symbol": symbol,
            "productType": product_type,
            "marginMode": "isolated",  # or "crossed"
            "marginCoin": "USDT",  # or other margin coins
            "size": str(size),
            "price": str(price) if price is not None else None,
            "side": side,
            "tradeSide": "open",
            "orderType": order_type,
        }
        return await self.post(path, json_body=body)

    async def cancel_all_orders(
        self,
        product_type: str = "USDT-FUTURES",
    ):
        """
        Cancel all orders for a given product type and symbol.
        """
        path = "/api/v2/mix/order/cancel-all-orders"
        body = {"productType": product_type}
        return await self.post(path, json_body=body)

    async def flash_close_position(
        self,
        symbol: str,
        product_type: str = "USDT-FUTURES",
        hold_side: str = "long",
    ):
        """
        Close all positions for a given symbol and hold side.
        """
        path = "/api/v2/mix/order/close-positions"
        body = {
            "symbol": symbol,
            "productType": product_type,
            "holdSide": hold_side,
        }
        return await self.post(path, json_body=body)