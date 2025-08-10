from aiohttp import TCPConnector
from bitget.typing import Granularity
from shared.http import TracingClientSession

class BitgetSpotMarketClient:

    def __init__(self, base_url: str = "https://api.bitget.com"):
        self._client = TracingClientSession(
            base_url=base_url,
            headers={"Content-Type": "application/json"},
            connector=TCPConnector(ssl=False)
        )

    async def get_candlesticks(self, symbol: str, granularity: Granularity = "1day", start_time: int = None, end_time: int = None, limit: int = 1000) -> dict:
        """
        Fetches candlestick data for a given symbol and granularity from the Bitget API.
        :param symbol: Trading pair e.g.BTCUSDT
        :param granularity: Time interval of charts For the corresponding relationship between granularity and value
        :param start_time: The time start point of the chart data, i.e., to get the chart data after this time stamp
        :param end_time: The time end point of the chart data, i.e., get the chart data before this time stamp
        :param limit: Number of queries: Default: 100, maximum: 1000.
        :return: A dictionary containing the candlestick data.
        """
        params = {
            "symbol": symbol,
            "granularity": granularity,
            "startTime": start_time,
            "endTime": end_time,
            "limit": limit
        }

        async with self._client.get("/api/v2/spot/market/candles", params=params) as resp:
            resp.raise_for_status()
            return await resp.json()


    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        # Close the underlying HTTP session
        await self._client.close()