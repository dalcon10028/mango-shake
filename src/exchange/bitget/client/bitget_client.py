import logging
import json
from typing import Any

from aiohttp import TCPConnector
from shared.http import TracingClientSession


class BitgetClient:
    def __init__(
            self,
            base_url: str,
            headers: dict | None = None,
    ):
        default_headers = headers or {
            "Content-Type": "application/json",
            "Accept": "application/json",
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

    async def _request(
            self,
            method: str,
            path: str,
            params: dict | None = None,
            json_body: dict | None = None,
            headers: dict | None = None,
    ) -> Any:
        headers = headers or {}
        session_method = getattr(self._client, method.lower())
        body_str = None
        if json_body is not None:
            body_str = json.dumps(json_body, separators=(",", ":"))
            if headers is None:
                headers = {}
            headers["Content-Type"] = "application/json"
        async with session_method(path, params=params, data=body_str, headers=headers) as resp:
            text = await resp.text()
            if resp.status != 200:
                raise RuntimeError(f"HTTP {resp.status}: {text}")
            content_type = resp.headers.get("Content-Type", "")
            if "application/json" in content_type:
                return await resp.json()
            return text

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
