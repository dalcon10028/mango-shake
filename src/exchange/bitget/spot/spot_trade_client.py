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
        {"code":"00000","msg":"success","requestTime":1695808949356,"data":[{"userId":"*********","symbol":"ETHUSDT","orderId":"*****************************","clientOid":"*****************************","price":"0","size":"20.0000000000000000","orderType":"market","side":"buy","status":"filled","priceAvg":"1598.1000000000000000","baseVolume":"0.0125000000000000","quoteVolume":"19.9762500000000000","enterPointSource":"WEB","feeDetail":"{\"newFees\":{\"c\":0,\"d\":0,\"deduction\":false,\"r\":-0.112079256,\"t\":-0.112079256,\"totalDeductionFee\":0},\"USDT\":{\"deduction\":false,\"feeCoinCode\":\"ETH\",\"totalDeductionFee\":0,\"totalFee\":-0.1120792560000000}}","orderSource":"market","cTime":"1698736299656","uTime":"1698736300363","tpslType":"normal","cancelReason":"","triggerPrice":null}]}
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