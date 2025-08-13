import logging

from collections import defaultdict
from typing import Any
from reactivex import Subject
from exchange.bitget.dto.websocket import SubscribeReq


class BitgetStreamManager:
    # symbol, interval
    candle_stream: dict[str, dict[str, Subject]] = defaultdict(dict)
    logger = logging.getLogger(__name__)

    def __init__(self, strategies: dict[str, Any]):
        self.channels = [
            SubscribeReq(
                inst_type=strat["product_type"],
                channel=f"candle{interval}",
                inst_id=symbol
            )
            for strat in strategies.values()
            for interval in strat["intervals"]
            for symbol in strat["universe"]
        ]