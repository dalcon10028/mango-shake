from shared.http.tracing_client_session import TracingClientSession

class UpbitCrixClient:

    def __init__(self, base_url: str = "https://crix-api-cdn.upbit.com"):
        self._client = TracingClientSession(base_url=base_url, headers={"Content-Type": "application/json"})

    async def get_daily_candles(self, symbol: str, count: int = 30):
        params = {
            "code": f"CRIX.UPBIT.KRW-{symbol}",
            "count": count,
        }

        async with self._client.get("/v1/crix/candles/days", params=params) as resp:
            resp.raise_for_status()
            return await resp.json()

    async def __aenter__(self) -> "UpbitCrixClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self._client.close()
