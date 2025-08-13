import hmac
import hashlib
import base64
from typing import Optional

def generate_signature(
    secret_key: str,
    timestamp: str,
    method: str,
    request_path: str,
    query_string: Optional[str] = "",
    body: Optional[str] = ""
) -> str:
    """
    Generate an HMAC-SHA256 signature, Base64-encoded.

    :param secret_key: Your API secret key.
    :param timestamp: Milliseconds since Epoch, as string.
    :param method: HTTP method, e.g. "GET" or "POST".
    :param request_path: API endpoint path, e.g. "/api/v2/mix/order/place-order".
    :param query_string: URL query string without the leading "?", e.g. "limit=20&symbol=BTCUSDT".
    :param body: JSON-serialized request body string, or empty.
    :return: Base64-encoded HMAC-SHA256 digest.
    """
    method = method.upper()
    path = request_path
    if query_string:
        path = f"{path}?{query_string}"
    payload = f"{timestamp}{method}{path}{body or ''}"
    mac = hmac.new(secret_key.encode('utf-8'), payload.encode('utf-8'), hashlib.sha256)
    return base64.b64encode(mac.digest()).decode('utf-8')