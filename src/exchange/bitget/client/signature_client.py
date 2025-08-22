import time
import logging

from aiohttp import TCPConnector
from exchange.bitget.utils.signature import generate_signature
from shared.http import TracingClientSession


class SignatureClient:
    def __init__(
            self,
            base_url: str,
            access_key: str,
            secret_key: str,
            passphrase: str,
    ):
        self._access_key = access_key
        self._secret_key = secret_key
        self._passphrase = passphrase

        default_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "ACCESS-KEY": access_key,
            "locale": "ko-KR",
        }
        connector = TCPConnector(ssl=False)
        self._client = TracingClientSession(
            base_url=base_url, headers=default_headers, connector=connector
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self._client.close()

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

        session_method = getattr(self._client, method.lower())
        async with session_method(path, params=params, data=body_str, headers=headers) as resp:
            if resp.status != 200:
                logging.error(f"HTTP Error {resp.status}: {await resp.text()}")
                raise RuntimeError(f"HTTP Error {resp.status}: {await resp.text()}")
            return await resp.json()

    async def get(
            self,
            path: str,
            params: dict[str, str] | None = None,
    ) -> dict:
        """
        Shortcut for GET requests.
        """
        return await self._request("GET", path, params=params)

    async def post(
            self,
            path: str,
            json_body: dict | None = None,
    ) -> dict:
        """
        Shortcut for POST requests.
        """
        return await self._request("POST", path, json_body=json_body)

    async def put(
            self,
            path: str,
            json_body: dict | None = None,
    ) -> dict:
        """
        Shortcut for PUT requests.
        """
        return await self._request("PUT", path, json_body=json_body)

    async def delete(
            self,
            path: str,
            params: dict[str, str] | None = None,
    ) -> dict:
        """
        Shortcut for DELETE requests.
        """
        return await self._request("DELETE", path, params=params)
