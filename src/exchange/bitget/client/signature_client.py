import time
import logging

from aiohttp import TCPConnector

from exchange.bitget.client.bitget_client import BitgetClient
from exchange.bitget.utils.signature import generate_signature
from shared.http import TracingClientSession


class SignatureClient(BitgetClient):
    def __init__(self, base_url: str, access_key: str, secret_key: str, passphrase: str):
        default_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "ACCESS-KEY": access_key,
            "locale": "ko-KR",
        }
        super().__init__(base_url=base_url, headers=default_headers)
        self._access_key = access_key
        self._secret_key = secret_key
        self._passphrase = passphrase

    def _sign(
            self,
            method: str,
            path: str,
            params: dict[str, str] | None = None,
            body: str = "",
    ) -> dict[str, str]:

        timestamp = str(int(time.time() * 1000))
        query_string = ""
        if params:
            # GET 은 params, POST 는 빈 스트링
            query_string = "&".join(f"{k}={v}" for k, v in params.items())
        sign = generate_signature(
            self._secret_key, timestamp, method, path, query_string, body
        )
        return {
            "ACCESS-KEY": self._access_key,
            "ACCESS-SIGN": sign,
            "ACCESS-TIMESTAMP": timestamp,
            "ACCESS-PASSPHRASE": self._passphrase,
        }

    async def _request(
            self,
            method: str,
            path: str,
            params: dict[str, str] | None = None,
            json_body: dict | None = None,
            headers: dict | None = None,
    ) -> dict:
        # Filter out None values from params to avoid sending empty parameters
        if params:
            params = {k: v for k, v in params.items() if v is not None}
        body_str = ""
        if json_body is not None:
            import json
            body_str = json.dumps(json_body, separators=(",", ":"))

        auth_headers = self._sign(method, path, params if method == "GET" else None, body_str)
        # aiohttp 의 session.get/post 에서 headers 병합
        headers = {**auth_headers}

        return await super()._request(
            method,
            path,
            params=params if method == "GET" else None,
            json_body=json_body if method != "GET" else None,
            headers=headers
        )
