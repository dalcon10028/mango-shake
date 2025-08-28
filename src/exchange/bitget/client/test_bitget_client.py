import json
import pytest
from aioresponses import aioresponses, CallbackResult

from exchange.bitget.client.bitget_client import BitgetClient

BASE_URL = "https://api.example.com"

@pytest.mark.asyncio
async def test_get_success_filters_none_params_and_returns_json():
    path = "/v1/ping"
    # params includes a None which should be filtered out by BitgetClient
    params = {"a": "1", "b": None}
    expected = {"ok": True}
    with aioresponses() as mocked:
        mocked.get(
            f"{BASE_URL}{path}?a=1",
            status=200,
            payload=expected,
            headers={"Content-Type": "application/json"},
        )
        async with BitgetClient(base_url=BASE_URL) as client:
            data = await client.get(path, params=params)
            assert data == expected


@pytest.mark.asyncio
async def test_post_success_sends_minified_json_body_and_parses_response():
    path = "/v1/order"
    req_body = {"x": 1, "y": "z"}
    expected = {"result": "ok"}

    def callback(url, **kwargs):
        sent_body = kwargs.get("data")
        # Ensure it is minified like json.dumps(..., separators=(",", ":"))
        assert sent_body == json.dumps(req_body, separators=(",", ":"))
        return CallbackResult(status=200, headers={"Content-Type": "application/json"}, body=json.dumps(expected))

    with aioresponses() as mocked:
        mocked.post(f"{BASE_URL}{path}", callback=callback)

        async with BitgetClient(base_url=BASE_URL) as client:
            data = await client.post(path, json_body=req_body)

    assert data == expected


@pytest.mark.asyncio
async def test_non_200_raises_runtime_error_with_status_and_body(monkeypatch):
    path = "/v1/fail"
    error_body = {"error": "bad"}

    with aioresponses() as mocked:
        mocked.get(
            f"{BASE_URL}{path}",
            status=400,
            body=json.dumps(error_body),
            headers={"Content-Type": "application/json"},
        )

        async with BitgetClient(base_url=BASE_URL) as client:
            with pytest.raises(RuntimeError) as exc:
                await client.get(path)

    msg = str(exc.value)
    assert "HTTP 400" in msg
    assert "bad" in msg


@pytest.mark.asyncio
async def test_context_manager_closes_session(monkeypatch):
    path = "/v1/ping"
    expected = {"ok": True}

    with aioresponses() as mocked:
        mocked.get(f"{BASE_URL}{path}", status=200, payload=expected)

        async with BitgetClient(base_url=BASE_URL) as client:
            # Monkeypatch the underlying close to verify it gets awaited on exit
            closed = {"value": False}

            async def fake_close():
                closed["value"] = True

            # swap close after client is constructed
            monkeypatch.setattr(client._client, "close", fake_close, raising=True)
            _ = await client.get(path)

        assert closed["value"] is True
