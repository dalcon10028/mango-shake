from bitget.typing import ProductType
from shared.tracing_client_session import TracingClientSession

class BitgetFutureMarketClient:

    def __init__(self, base_url: str, product_type: ProductType):
        self._client = TracingClientSession(base_url=base_url, headers={"Content-Type": "application/json"})
        self._product_type = product_type

    async def get_contract_config(self, symbol: str):
        async with self._client.get("/api/v2/mix/market/contracts", params={ "productType": self._product_type, "symbol": symbol }) as resp:
            resp.raise_for_status()
            return await resp.json()

    async def close(self):
        await self._client.close()

    async def __aenter__(self) -> "BitgetFutureMarketClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()
