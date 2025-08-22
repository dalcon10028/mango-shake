from datetime import datetime
from typing import Optional

from aiohttp import TCPConnector

from bitget.typing import ProductType
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
