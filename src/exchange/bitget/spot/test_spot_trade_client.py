import re
import pytest
from aioresponses import aioresponses
from exchange.bitget.spot.spot_trade_client import BitgetSpotTradeClient

BASE_URL = "https://api.bitget.com"

@pytest.mark.asyncio
async def test_get_history_orders_returns_example_payload():
    payload = {
        "code": "00000",
        "msg": "success",
        "requestTime": 1695808949356,
        "data": [{
            "userId": "*********",
            "symbol": "ETHUSDT",
            "orderId": "*****************************",
            "clientOid": "*****************************",
            "price": "0",
            "size": "20.0000000000000000",
            "orderType": "market",
            "side": "buy",
            "status": "filled",
            "priceAvg": "1598.1000000000000000",
            "baseVolume": "0.0125000000000000",
            "quoteVolume": "19.9762500000000000",
            "enterPointSource": "WEB",
            "feeDetail": "{\"newFees\":{\"c\":0,\"d\":0,\"deduction\":false,\"r\":-0.112079256,\"t\":-0.112079256,\"totalDeductionFee\":0},\"USDT\":{\"deduction\":false,\"feeCoinCode\":\"ETH\",\"totalDeductionFee\":0,\"totalFee\":-0.1120792560000000}}",
            "orderSource": "market",
            "cTime": "1698736299656",
            "uTime": "1698736300363",
            "tpslType": "normal",
            "cancelReason": "",
            "triggerPrice": None
        }]
    }

    with aioresponses() as m:
        m.get(re.compile(rf"{re.escape(BASE_URL)}/api/v2/spot/trade/history-orders.*"), status=200, payload=payload, headers={"Content-Type": "application/json"})

        async with BitgetSpotTradeClient(
            base_url=BASE_URL,
            access_key="ak",
            secret_key="sk",
            passphrase="pp",
        ) as client:
            resp = await client.get_history_orders(symbol="ETHUSDT")

    assert resp == payload