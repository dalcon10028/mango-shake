import asyncio
import json
import logging
import uuid
import aiohttp


# Helper to mask sensitive header values for logging
def _mask_sensitive_headers(headers: dict) -> dict:
    """Return a copy of headers with sensitive values masked."""
    masked = {}
    for k, v in headers.items():
        upper_k = k.upper()
        if upper_k in ("ACCESS-KEY", "ACCESS-SIGN", "ACCESS-PASSPHRASE"):
            # Fully mask sensitive values
            masked[k] = "****"
        else:
            masked[k] = v
    return masked

def _mask_sensitive_body(body: str) -> str:
    """Return a copy of body with sensitive values masked."""
    try:
        data = json.loads(body)
        if isinstance(data, dict):
            for k in data.keys():
                upper_k = k.upper()
                if upper_k in ("APPKEY", "SECRETKEY"):
                    data[k] = "****"
        return json.dumps(data)
    except Exception:
        return body  # If body is not JSON, return as is

logger = logging.getLogger("aiohttp.client")

class TracingClientSession(aiohttp.ClientSession):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, trace_configs=[trace_config])

    async def _request(self, method, url, *args, **kwargs):
        trace_request_ctx = kwargs.pop("trace_request_ctx", {})
        trace_id = str(uuid.uuid4())
        trace_request_ctx["trace_id"] = trace_id
        kwargs["trace_request_ctx"] = trace_request_ctx

        headers = kwargs.get("headers", {})

        # Filter out None values from params to avoid sending empty parameters
        if "params" in kwargs and kwargs["params"]:
            kwargs["params"] = {k: v for k, v in kwargs["params"].items() if v is not None}


        # Mask sensitive header values before logging
        masked_headers = _mask_sensitive_headers(headers)

        # 요청 바디 로깅 처리
        body_repr = None
        if method.upper() in ("POST", "PUT", "PATCH"):
            if "json" in kwargs:
                try:
                    body_repr = json.dumps(kwargs["json"])
                except Exception:
                    body_repr = str(kwargs["json"])
            elif "data" in kwargs:
                body_repr = str(kwargs["data"])

        logger.debug(f"[{trace_id}] ---> {method} {url}")
        logger.debug(f"[{trace_id}] Headers: {masked_headers}")
        if body_repr:
            body_repr = _mask_sensitive_body(body_repr)
            logger.debug(f"[{trace_id}] Request Body: {body_repr}")

        return await super()._request(method, url, *args, **kwargs)


async def on_request_start(session, trace_config_ctx, params):
    trace_id = trace_config_ctx.trace_request_ctx.get("trace_id", "unknown")
    trace_config_ctx.start_time = asyncio.get_event_loop().time()
    trace_config_ctx.trace_id = trace_id
    trace_config_ctx.method = params.method
    trace_config_ctx.url = str(params.url)


async def on_request_end(session, trace_config_ctx, params):
    trace_id = trace_config_ctx.trace_id
    duration = (asyncio.get_event_loop().time() - trace_config_ctx.start_time) * 1000
    logger.debug(f"[{trace_id}] <--- END HTTP ({duration:.0f}ms)")


async def on_request_exception(session, trace_config_ctx, params):
    trace_id = trace_config_ctx.trace_request_ctx.get("trace_id", "unknown")
    logger.error(f"[{trace_id}] !!! EXCEPTION during {params.method} {params.url}")


trace_config = aiohttp.TraceConfig()
trace_config.on_request_start.append(on_request_start)
trace_config.on_request_end.append(on_request_end)
trace_config.on_request_exception.append(on_request_exception)
