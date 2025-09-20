import logging
from functools import cache
from typing import Optional, Dict, Any

from exchange.bitget.client.bitget_client import BitgetClient

logger = logging.getLogger(__name__)


class KiwoomRestClient(BitgetClient):
    def __init__(
            self,
            base_url: str,
            app_key: str,
            app_secret: str,
    ):
        super().__init__(base_url=base_url)
        self.app_key = app_key
        self.app_secret = app_secret

    async def _request(self, method, path, params=None, json_body=None, headers=None):
        res = await super()._request(method, path, params, json_body, headers)
        if res.get("return_code", -1) != 0:
            raise Exception(f"Kiwoom API Error: {res}")
        return res

    @cache
    async def get_access_token(self) -> str:
        """
        접근토큰발급
        {"expires_dt":"20241107083713","token_type":"bearer","token":"WQJCwyqInphKnR3bSRtB9NE1lv...","return_code":0,"return_msg":"정상적으로 처리되었습니다"}
        """
        path = "/oauth2/token"
        body = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "secretkey": self.app_secret,
        }
        data = await self.post(path, body)
        return data["token"]

    async def get_daily_candles(self, symbol: str, date: str) -> Optional[Dict[str, Any]]:
        """일별 주가 요청"""
        headers = {
            "authorization": f"Bearer {await self.get_access_token()}",
            "tr-id": "DOSTKMRKCOND",
        }
        params = {
            "stk_cd": symbol,
            "qry_dt": date,
            "indc_tp": "0",
        }
        async with self.session.post(
            f"{self.base_url}/api/dostk/mrkcond", headers=headers, json=params
        ) as response:
            if response.status == 200:
                return await response.json()
            else:
                logger.error(f"Error fetching daily candles for {symbol} on {date}: {response.status} {await response.text()}")
                return None