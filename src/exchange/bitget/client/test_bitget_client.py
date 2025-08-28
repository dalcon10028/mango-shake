import json
import pytest
from aioresponses import aioresponses, CallbackResult

from exchange.bitget.client.bitget_client import BitgetClient
from exchange.bitget.dto.bitget_error import BitgetError, BitgetErrorCode

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
async def test_non_200_raises_bitget_error_and_parses_body(monkeypatch):
    path = "/v1/fail"
    error_body = {"code": "40762", "msg": "The order amount exceeds the balance", "requestTime": 1756346471768, "data": None}

    with aioresponses() as mocked:
        mocked.get(
            f"{BASE_URL}{path}",
            status=400,
            payload=error_body,
            headers={"Content-Type": "application/json"},
        )

        async with BitgetClient(base_url=BASE_URL) as client:
            with pytest.raises(BitgetError) as exc:
                await client.get(path)

    err = exc.value
    assert isinstance(err, BitgetError)
    assert err.code == BitgetErrorCode.INSUFFICIENT_BALANCE
    assert err.msg == error_body["msg"]
    assert err.request_time == error_body["requestTime"]
    assert err.data == error_body["data"]
    # message format includes enum name and value
    s = str(err)
    assert "INSUFFICIENT_BALANCE" in s and "40762" in s and error_body["msg"] in s


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
