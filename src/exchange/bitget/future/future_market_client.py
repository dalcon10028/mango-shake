from datetime import datetime
from typing import Optional

from aiohttp import TCPConnector

from exchange.bitget.typing import ProductType
from shared.http.tracing_client_session import TracingClientSession

class BitgetFutureMarketClient:

    def __init__(self, base_url: str, product_type: ProductType):
        connector = TCPConnector(ssl=False)
        self._client = TracingClientSession(base_url=base_url, headers={"Content-Type": "application/json"}, connector=connector)
        self._product_type = product_type

    async def get_contract_config(self, symbol: str):
        async with self._client.get("/api/v2/mix/market/contracts", params={ "productType": self._product_type, "symbol": symbol }) as resp:
            resp.raise_for_status()
            return await resp.json()

    async def ticker(self, symbol: str):
        """
        Get ticker information for a specific symbol.
        {"code":"00000","msg":"success","requestTime":1695794095685,"data":[{"symbol":"ETHUSD_231229","lastPr":"1829.3","askPr":"1829.8","bidPr":"1829.3","bidSz":"0.054","askSz":"0.785","high24h":"0","low24h":"0","ts":"1695794098184","change24h":"0","baseVolume":"0","quoteVolume":"0","usdtVolume":"0","openUtc":"0","changeUtc24h":"0","indexPrice":"1822.15","fundingRate":"0","holdingAmount":"9488.49","deliveryStartTime":"1693538723186","deliveryTime":"1703836799000","deliveryStatus":"delivery_normal","open24h":"0","markPrice":"1829"}]}
        """
        async with self._client.get("/api/v2/mix/market/ticker", params={ "productType": "USDT-FUTURES", "symbol": symbol }) as resp:
            resp.raise_for_status()
            return await resp.json()

    async def get_klines(self, symbol: str, granularity: str, product_type: str = 'USDT-FUTURES', start_time: Optional[datetime] = None, end_time: Optional[datetime] = None, limit: int = 1000):
        params = {
            "symbol": symbol,
            "productType": product_type,
            "granularity": granularity,
            "limit": limit,
            "startTime": start_time,
            "endTime": end_time
        }

        async with self._client.get("/api/v2/mix/market/history-candles", params=params) as resp:
            resp.raise_for_status()
            res = await resp.json()
            return res.get("data", [])

    async def close(self):
        await self._client.close()

    async def __aenter__(self) -> "BitgetFutureMarketClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()
