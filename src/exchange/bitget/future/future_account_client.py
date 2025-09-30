from typing import Any

from exchange.bitget.client import SignatureClient


class BitgetFutureAccountClient(SignatureClient):

    def __init__(self, base_url: str, access_key: str, secret_key: str, passphrase: str):
        super().__init__(base_url, access_key, secret_key, passphrase)

    async def __aenter__(self) -> "BitgetFutureAccountClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self._client.close()

    async def get_accounts(
        self,
        product_type: str,
    ) -> dict[str, Any]:
        """
        Get account information for futures trading.
        {'code': '00000', 'data': [{'accountEquity': '36.07827483', 'assetList': [], 'assetMode': 'single', 'available': '1.28556483', 'btcEquity': '0.000312946601', 'coupon': '0', 'crossedMargin': '0', 'crossedMaxAvailable': '1.28556483', 'crossedRiskRate': '0', 'crossedUnrealizedPL': '', 'grant': '0', 'isolatedMargin': '34.54821', 'isolatedMaxAvailable': '1.28556483', 'isolatedUnrealizedPL': '', 'locked': '0', 'marginCoin': 'USDT', 'maxTransferOut': '1.28556483', 'unionAvailable': '1.28556483', 'unionMm': '0', 'unionTotalMargin': '36.07827483', 'unrealizedPL': '0.2445', 'usdtEquity': '36.07827483176'}], 'msg': 'success', 'requestTime': 1755580537633}
        """
        path = "/api/v2/mix/account/accounts"
        params = {"productType": product_type}
        res = await self.get(path, params=params)
        return next(filter(lambda x: x["marginCoin"] == "USDT", res["data"]), {})

    async def get_account(
        self,
        symbol: str,
        product_type: str,
        margin_coin: str = "USDT",
    ) -> dict[str, Any]:
        """
        Get leverage setting for a specific symbol.
        Returns leverage configuration for the symbol.
        """
        path = "/api/v2/mix/account/account"
        params = {
            "symbol": symbol,
            "productType": product_type,
            "marginCoin": margin_coin
        }
        res = await self.get(path, params=params)
        return res.get("data", {})
