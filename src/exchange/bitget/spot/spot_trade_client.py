from datetime import datetime
from typing import Optional

from exchange.bitget.client.signature_client import SignatureClient


class BitgetSpotTradeClient(SignatureClient):

    def __init__(
            self,
            base_url: str,
            access_key: str,
            secret_key: str,
            passphrase: str,
    ):
        super().__init__(base_url, access_key, secret_key, passphrase)


    async def get_history_orders(
        self,
        symbol: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        id_less_than: Optional[str] = None,
        limit: int = 100,
        order_id: Optional[str] = None,
        tpsl_type: Optional[str] = None,
        request_time: Optional[int] = None,
        receive_window: Optional[int] = None,
    ) -> dict:
        """
        Fetch historical spot orders (up to 90 days) from Bitget.
        """
        path = "/api/v2/spot/trade/history-orders"

        params = {
            "symbol": symbol,
            "startTime": str(int(start_time.timestamp() * 1000)) if start_time else None,
            "endTime": str(int(end_time.timestamp() * 1000)) if end_time else None,
            "idLessThan": id_less_than,
            "limit": limit,
            "orderId": order_id,
            "tpslType": tpsl_type,
            "requestTime": request_time,
            "receiveWindow": receive_window
        }

        return await self.get(path, params=params)