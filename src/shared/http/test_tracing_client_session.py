import json
import logging
import pytest

from aioresponses import aioresponses
from shared.http.tracing_client_session import _mask_sensitive_headers, TracingClientSession


@pytest.mark.parametrize("headers, expected", [
    (
        {
            "ACCESS-KEY": "mykey123456",
            "ACCESS-SIGN": "signaturevalue",
            "ACCESS-PASSPHRASE": "secretpass",
            "Content-Type": "application/json",
            "Custom": "value"
        },
        {
            "ACCESS-KEY": "****",
            "ACCESS-SIGN": "****",
            "ACCESS-PASSPHRASE": "****",
            "Content-Type": "application/json",
            "Custom": "value"
        }
    ),
])
def test_mask_sensitive_headers(headers, expected):
    masked = _mask_sensitive_headers(headers)
    assert masked == expected

@pytest.mark.asyncio
async def test_request_logs_masked_headers(caplog):
    # Capture DEBUG logs from aiohttp.client logger
    caplog.set_level(logging.DEBUG, logger="aiohttp.client")

    async with TracingClientSession() as session:
        url = "http://example.com/test"
        # Set up aioresponses to mock the GET
        with aioresponses() as m:
            m.get(
                url,
                status=200,
                body=json.dumps({"ok": True}),
                headers={"Content-Type": "application/json"}
            )
            # Perform request with sensitive headers
            async with session.get(
                url,
                headers={
                    "ACCESS-KEY": "mykey123456",
                    "ACCESS-SIGN": "signaturevalue",
                    "ACCESS-PASSPHRASE": "secretpass",
                    "Content-Type": "application/json"
                }
            ) as resp:
                # Consume response to trigger logging
                await resp.text()

    # Verify that logs include masked headers, not raw values
    found_mask = False
    for record in caplog.records:
        if "Headers:" in record.getMessage():
            msg = record.getMessage()
            assert "mykey123456" not in msg
            assert "signaturevalue" not in msg
            assert "secretpass" not in msg
            assert "'ACCESS-KEY': '****'" in msg
            found_mask = True
    assert found_mask, "Did not find any logged Headers lines"
