import hmac
import hashlib
import base64
import pytest

from bitget.utils.signature import generate_signature

@pytest.mark.parametrize("method, path, query, body", [
    ("GET", "/api/mix/v2/market/depth", "", ""),
    ("GET", "/api/mix/v2/market/depth", "limit=20&symbol=BTCUSDT", ""),
    ("POST", "/api/v2/mix/order/place-order", "", '{"size":"8","symbol":"BTCUSDT"}'),
    ("POST", "/api/v2/mix/order/place-order", "limit=5", '{"size":"8","symbol":"BTCUSDT"}'),
])
def test_generate_signature_hmac(method, path, query, body):
    secret = "mysecret"
    timestamp = "16273667805456"
    sig = generate_signature(secret, timestamp, method, path, query, body)
    # Compute expected value
    method_up = method.upper()
    full_path = f"{path}?{query}" if query else path
    payload = f"{timestamp}{method_up}{full_path}{body or ''}"
    expected = base64.b64encode(
        hmac.new(secret.encode('utf-8'), payload.encode('utf-8'), hashlib.sha256).digest()
    ).decode('utf-8')
    assert sig == expected