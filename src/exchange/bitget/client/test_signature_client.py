import json
import pytest
from aioresponses import aioresponses, CallbackResult

from exchange.bitget.client.signature_client import SignatureClient

BASE_URL = "https://api.example.com"
ACCESS_KEY = "ak_test"
SECRET_KEY = "sk_test"
PASSPHRASE = "pp_test"


@pytest.mark.asyncio
async def test_get_includes_signed_headers_and_filters_params(monkeypatch):
    # Freeze time to make ACCESS-TIMESTAMP deterministic
    fixed_ts_sec = 1_720_000_000.0  # -> 1720000000000 ms
    monkeypatch.setattr("time.time", lambda: fixed_ts_sec)

    # Capture inputs passed to generate_signature and return a fixed sign
    captured = {}

    def fake_generate_signature(secret, timestamp, method, path, query_string, body):
        captured.update(
            secret=secret,
            timestamp=timestamp,
            method=method,
            path=path,
            query_string=query_string,
            body=body,
        )
        return "sig-fixed"

    monkeypatch.setattr(
        "exchange.bitget.client.signature_client.generate_signature",
        fake_generate_signature,
        raising=True,
    )

    path = "/v1/ping"
    params = {"a": "1", "b": None, "c": "hello"}  # b=None should be removed
    expected = {"ok": True}

    def cb(url, **kwargs):
        # aioresponses delivers headers under kwargs["headers"], body under kwargs["data"]
        req_headers = kwargs.get("headers") or {}
        # Check signed headers
        assert req_headers["ACCESS-KEY"] == ACCESS_KEY
        assert req_headers["ACCESS-SIGN"] == "sig-fixed"
        assert req_headers["ACCESS-TIMESTAMP"] == str(int(fixed_ts_sec * 1000))
        assert req_headers["ACCESS-PASSPHRASE"] == PASSPHRASE
        # GET should not send a body
        assert kwargs.get("data") in (None, "")
        return CallbackResult(
            status=200,
            headers={"Content-Type": "application/json"},
            body=json.dumps(expected),
        )

    with aioresponses() as mocked:
        # Expect filtered params (b removed) in the URL
        mocked.get(f"{BASE_URL}{path}?a=1&c=hello", callback=cb)

        async with SignatureClient(
            base_url=BASE_URL,
            access_key=ACCESS_KEY,
            secret_key=SECRET_KEY,
            passphrase=PASSPHRASE,
        ) as client:
            data = await client.get(path, params=params)

    # Response passthrough
    assert data == expected

    # Verify inputs that were signed
    assert captured["secret"] == SECRET_KEY
    assert captured["timestamp"] == str(int(fixed_ts_sec * 1000))
    assert captured["method"] == "GET"
    assert captured["path"] == path
    # Query string should be built from filtered params in insertion order from dict (Py3.7+ preserves)
    # Our client builds: "a=1&c=hello"
    assert captured["query_string"] == "a=1&c=hello"
    # GET signing should have empty body string
    assert captured["body"] == ""


@pytest.mark.asyncio
async def test_post_signs_body_minified_and_not_params(monkeypatch):
    fixed_ts_sec = 1_720_000_001.0
    monkeypatch.setattr("time.time", lambda: fixed_ts_sec)

    captured = {}

    def fake_generate_signature(secret, timestamp, method, path, query_string, body):
        captured.update(
            secret=secret,
            timestamp=timestamp,
            method=method,
            path=path,
            query_string=query_string,
            body=body,
        )
        return "sig-post"

    monkeypatch.setattr(
        "exchange.bitget.client.signature_client.generate_signature",
        fake_generate_signature,
        raising=True,
    )

    path = "/v1/order"
    body = {"x": 1, "y": "z"}
    # Even if params are provided, POST should sign with empty query_string
    params = {"ignored": "param"}
    expected = {"result": "ok"}

    def cb(url, **kwargs):
        req_headers = kwargs.get("headers") or {}
        sent_body = kwargs.get("data")
        # Body must be minified JSON
        assert sent_body == json.dumps(body, separators=(",", ":"))
        # Signed headers present
        assert req_headers["ACCESS-KEY"] == ACCESS_KEY
        assert req_headers["ACCESS-SIGN"] == "sig-post"
        assert req_headers["ACCESS-TIMESTAMP"] == str(int(fixed_ts_sec * 1000))
        assert req_headers["ACCESS-PASSPHRASE"] == PASSPHRASE
        return CallbackResult(
            status=200,
            headers={"Content-Type": "application/json"},
            body=json.dumps(expected),
        )

    with aioresponses() as mocked:
        mocked.post(f"{BASE_URL}{path}", callback=cb)

        async with SignatureClient(
            base_url=BASE_URL,
            access_key=ACCESS_KEY,
            secret_key=SECRET_KEY,
            passphrase=PASSPHRASE,
        ) as client:
            # params should be ignored at transport level for POST in our client
            data = await client.post(path, json_body=body)

    assert data == expected
    # Check that query_string used for signing is empty and body is minified
    assert captured["method"] == "POST"
    assert captured["path"] == path
    assert captured["query_string"] == ""
    assert captured["body"] == json.dumps(body, separators=(",", ":"))


@pytest.mark.asyncio
async def test_error_bubbles_with_http_status_and_body(monkeypatch):
    fixed_ts_sec = 1_720_000_002.0
    monkeypatch.setattr("time.time", lambda: fixed_ts_sec)
    monkeypatch.setattr(
        "exchange.bitget.client.signature_client.generate_signature",
        lambda *a, **k: "sig-err",
        raising=True,
    )

    path = "/v1/fail"
    error_body = {"error": "bad"}

    def cb(url, **kwargs):
        return CallbackResult(
            status=400,
            headers={"Content-Type": "application/json"},
            body=json.dumps(error_body),
        )

    with aioresponses() as mocked:
        mocked.get(f"{BASE_URL}{path}", callback=cb)
        async with SignatureClient(
            base_url=BASE_URL,
            access_key=ACCESS_KEY,
            secret_key=SECRET_KEY,
            passphrase=PASSPHRASE,
        ) as client:
            with pytest.raises(RuntimeError) as exc:
                await client.get(path)

    msg = str(exc.value)
    assert "HTTP 400" in msg
    assert json.dumps(error_body) in msg
