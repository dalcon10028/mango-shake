from typing import Any

from exchange.bitget.client import SignatureClient


class BitgetFuturePositionClient(SignatureClient):

    def __init__(self, base_url: str, access_key: str, secret_key: str, passphrase: str):
        super().__init__(base_url, access_key, secret_key, passphrase)

    async def __aenter__(self) -> "BitgetFuturePositionClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self._client.close()

    async def get_historical_position(
        self,
        product_type: str,
    ) -> list[dict[str, Any]]:
        """
        Get historical position information for futures trading.
        {'code': '00000', 'data': {'endId': '1336070763588493313', 'list': [{'closeAvgPrice': '118469.5', 'closeFee': '-0.13268584', 'closeTotalPos': '0.0028', 'ctime': '1754811613465', 'holdSide': 'long', 'marginCoin': 'USDT', 'marginMode': 'isolated', 'netProfit': '1.86719867', 'openAvgPrice': '117696.4', 'openFee': '-0.13181996', 'openTotalPos': '0.0028', 'pnl': '2.16468', 'posMode': 'hedge_mode', 'positionId': '1338342397607288854', 'symbol': 'BTCUSDT', 'totalFunding': '-0.03297551', 'utime': '1754831063207'}, {'closeAvgPrice': '4029.72', 'closeFee': '-0.37073424', 'closeTotalPos': '0.23', 'ctime': '1754585253017', 'holdSide': 'short', 'marginCoin': 'USDT', 'marginMode': 'crossed', 'netProfit': '-57.44831988', 'openAvgPrice': '3781.69', 'openFee': '-0.34791548', 'openTotalPos': '0.23', 'pnl': '-57.0469', 'posMode': 'hedge_mode', 'positionId': '1337392973074800656', 'symbol': 'ETHUSDT', 'totalFunding': '0.31722983', 'utime': '1754706763040'}, {'closeAvgPrice': '3783.35', 'closeFee': '-0.3329348', 'closeTotalPos': '0.22', 'ctime': '1754585123630', 'holdSide': 'short', 'marginCoin': 'USDT', 'marginMode': 'crossed', 'netProfit': '4.5240536', 'openAvgPrice': '3806.95', 'openFee': '-0.3350116', 'openTotalPos': '0.22', 'pnl': '5.192', 'posMode': 'hedge_mode', 'positionId': '1337392430386388999', 'symbol': 'ETHUSDT', 'totalFunding': '0', 'utime': '1754585248930'}, {'closeAvgPrice': '3807.92', 'closeFee': '-0.31986528', 'closeTotalPos': '0.21', 'ctime': '1754584625427', 'holdSide': 'short', 'marginCoin': 'USDT', 'marginMode': 'crossed', 'netProfit': '3.96162816', 'openAvgPrice': '3829.84', 'openFee': '-0.32170656', 'openTotalPos': '0.21', 'pnl': '4.6032', 'posMode': 'hedge_mode', 'positionId': '1337390340771553288', 'symbol': 'ETHUSDT', 'totalFunding': '0', 'utime': '1754585117733'}, {'closeAvgPrice': '113309', 'closeFee': '-0.2719416', 'closeTotalPos': '0.006', 'ctime': '1754440257025', 'holdSide': 'long', 'marginCoin': 'USDT', 'marginMode': 'isolated', 'netProfit': '-3.83379864', 'openAvgPrice': '113857.1', 'openFee': '-0.27325704', 'openTotalPos': '0.006', 'pnl': '-3.2886', 'posMode': 'hedge_mode', 'positionId': '1336784815805571080', 'symbol': 'BTCUSDT', 'totalFunding': '0', 'utime': '1754455105141'}, {'closeAvgPrice': '113229.2', 'closeFee': '-0.24457507', 'closeTotalPos': '0.0054', 'ctime': '1754405517343', 'holdSide': 'short', 'marginCoin': 'USDT', 'marginMode': 'isolated', 'netProfit': '-3.15878968', 'openAvgPrice': '112728.3', 'openFee': '-0.24349312', 'openTotalPos': '0.0054', 'pnl': '-2.70486', 'posMode': 'hedge_mode', 'positionId': '1336639107018399756', 'symbol': 'BTCUSDT', 'totalFunding': '0.03413851', 'utime': '1754411443199'}, {'closeAvgPrice': '3.0123', 'closeFee': '-0.3855744', 'closeTotalPos': '320', 'ctime': '1754390824474', 'holdSide': 'long', 'marginCoin': 'USDT', 'marginMode': 'isolated', 'netProfit': '-20.2029184', 'openAvgPrice': '3.073', 'openFee': '-0.393344', 'openTotalPos': '320', 'pnl': '-19.424', 'posMode': 'hedge_mode', 'positionId': '1336577480659181571', 'symbol': 'XRPUSDT', 'totalFunding': '0', 'utime': '1754397587344'}, {'closeAvgPrice': '3.0245', 'closeFee': '-0.1221898', 'closeTotalPos': '101', 'ctime': '1754240940320', 'holdSide': 'long', 'marginCoin': 'USDT', 'marginMode': 'crossed', 'netProfit': '10.26291384', 'openAvgPrice': '2.9204', 'openFee': '-0.11798416', 'openTotalPos': '101', 'pnl': '10.5141', 'posMode': 'hedge_mode', 'positionId': '1335948820952522753', 'symbol': 'XRPUSDT', 'totalFunding': '-0.01101219', 'utime': '1754270013710'}]}, 'msg': 'success', 'requestTime': 1755581243451}
        """
        path = "/api/v2/mix/position/history-position"
        params = {"productType": product_type, "limit": 100}
        res = await self.get(path, params=params)
        return res["data"]["list"]

    async def get_position(self, symbol: str, product_type: str = 'USDT-FUTURES') -> list[dict[str, Any]]:
        """
        Get current position for a specific symbol in futures trading.

        """
        path = "/api/v2/mix/position/single-position"
        params = {"symbol": symbol, "productType": product_type, "marginCoin": "USDT"}
        res = await self.get(path, params=params)
        return res["data"]

    async def get_positions(
            self,
            product_type: str,
    ) -> list[dict[str, Any]]:
        """
        Get current positions for futures trading.
        {'code': '00000', 'data': [{'achievedProfits': '0', 'assetMode': 'single', 'autoMargin': 'off', 'available': '0.0031', 'breakEvenPrice': '114987.353101240497', 'cTime': '1755590192436', 'deductedFee': '0.142470296', 'grant': '', 'holdSide': 'long', 'keepMarginRate': '0.004', 'leverage': '10', 'liquidationPrice': '103862.856568903174', 'locked': '0', 'marginCoin': 'USDT', 'marginMode': 'isolated', 'marginRatio': '0.044000344665', 'marginSize': '35.617574', 'markPrice': '114895.3', 'openDelegateSize': '0', 'openPriceAvg': '114895.4', 'posMode': 'hedge_mode', 'stopLoss': '', 'stopLossId': '', 'symbol': 'BTCUSDT', 'takeProfit': '', 'takeProfitId': '', 'total': '0.0031', 'totalFee': '', 'uTime': '1755590192436', 'unrealizedPL': '-0.00031'}], 'msg': 'success', 'requestTime': 1755590197975}
        """
        path = "/api/v2/mix/position/all-position"
        params = {"productType": product_type}
        res = await self.get(path, params=params)
        return res["data"]
