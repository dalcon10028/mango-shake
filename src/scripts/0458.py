import asyncio
import logging

from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN
from dependency_injector.wiring import inject, Provide
from exchange.bitget import BitgetFutureMarketClient, BitgetFutureTradeClient
from exchange.bitget.dto.bitget_error import BitgetError, BitgetErrorCode
from exchange.bitget.future.future_position_client import BitgetFuturePositionClient
from shared.containers import Container

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

ENTRY_AMOUNT = Decimal("500")
SYMBOL = "BTCUSDT"


@dataclass(frozen=True)
class Candle:
    start_time: int  # timestamp in milliseconds
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal

    @property
    def is_bullish(self) -> bool:
        return self.close > self.open

    @property
    def is_bearish(self) -> bool:
        return self.close < self.open

    @property
    def body_size(self) -> Decimal:
        return abs(self.close - self.open)

    @property
    def change_rate(self) -> Decimal:
        if self.open == 0:
            return Decimal(0)
        return (self.close - self.open) / self.open * Decimal(100)


def _calc_tick_and_steps() -> tuple[Decimal, Decimal, Decimal, Decimal]:
    """Return (tick, qty_step, min_trade_num, min_trade_usdt)."""
    spec = {
        "symbol": "BTCUSDT",
        "baseCoin": "BTC",
        "quoteCoin": "USDT",
        "buyLimitPriceRatio": "0.05",
        "sellLimitPriceRatio": "0.05",
        "feeRateUpRatio": "0.005",
        "makerFeeRate": "0.0002",
        "takerFeeRate": "0.0006",
        "openCostUpRatio": "0.01",
        "supportMarginCoins": ["USDT"],
        "minTradeNum": "0.0001",
        "priceEndStep": "1",
        "volumePlace": "4",
        "pricePlace": "1",
        "sizeMultiplier": "0.0001",
        "symbolType": "perpetual",
        "minTradeUSDT": "5",
        "maxSymbolOrderNum": "200",
        "maxProductOrderNum": "1000",
        "maxPositionNum": "150",
        "symbolStatus": "normal",
        "offTime": "-1",
        "limitOpenTime": "-1",
        "deliveryTime": "",
        "deliveryStartTime": "",
        "deliveryPeriod": "",
        "launchTime": "",
        "fundInterval": "8",
        "minLever": "1",
        "maxLever": "125",
        "posLimit": "0.1",
        "maintainTime": "",
        "openTime": "",
        "maxMarketOrderQty": "220",
        "maxOrderQty": "1200",
    }

    price_place = int(spec.get("pricePlace", "1"))
    price_end_step = Decimal(str(spec.get("priceEndStep", "1")))
    # tick = 10^-pricePlace * priceEndStep
    tick = (Decimal(1) / (Decimal(10) ** price_place)) * price_end_step

    # size step: prefer sizeMultiplier; fallback to 10^-volumePlace
    if spec.get("sizeMultiplier") is not None:
        qty_step = Decimal(str(spec["sizeMultiplier"]))
    else:
        vp = int(spec.get("volumePlace", "4"))
        qty_step = Decimal(1) / (Decimal(10) ** vp)

    min_trade_num = Decimal(str(spec.get("minTradeNum", "0")))
    min_trade_usdt = Decimal(str(spec.get("minTradeUSDT", "0")))
    return tick, qty_step, min_trade_num, min_trade_usdt


def _round_to_step(x: Decimal, step: Decimal) -> Decimal:
    if step == 0:
        return x
    return (x / step).to_integral_value(rounding=ROUND_DOWN) * step


@inject
async def main(
    market_client: BitgetFutureMarketClient = Provide[
        Container.bitget_future_market_client
    ],
    position_client: BitgetFuturePositionClient = Provide[
        Container.bitget_future_position_client
    ],
    trade_client: BitgetFutureTradeClient = Provide[
        Container.bitget_future_trade_client
    ],
):
    # 현재 주문 모두 취소, 대기 주문 없는 경우 에러
    # {"code":"22001","msg":"No order to cancel","requestTime":1755882462519,"data":null}

    res = None  # 안전용 초기화

    try:
        res = await trade_client.cancel_all_orders()  # 모든 주문 취소
        logger.info(f"모든 주문 취소 결과: {res}")
    except BitgetError as e:
        if e.code == BitgetErrorCode.NO_ORDER_TO_CANCEL:
            logger.info("대기 주문 없음, 건너뜀")
        else:
            logger.error(f"주문 취소 중 오류 발생: {e}")
            return

    # 최근 21개 1시간봉 조회 (현재 진행 중인 봉 포함)
    # 인덱스는 빠른시간순
    klines = await market_client.get_klines(symbol=SYMBOL, granularity="1H", limit=20)
    klines = [
        *map(
            lambda k: Candle(
                start_time=k[0],
                open=Decimal(k[1]),
                high=Decimal(k[2]),
                low=Decimal(k[3]),
                close=Decimal(k[4]),
                volume=Decimal(k[5]),
            ),
            klines,
        )
    ]

    if len(klines) < 3:
        logger.error(f"Kline 데이터가 부족합니다: {len(klines)}")
        return

    ticker = await market_client.ticker(SYMBOL)

    # 하락캔들이면서, 20개 캔들 평균보다 길이가 긴 캔들인 경우 매수 점검

    # 20개 캔들 평균 (인덱스 0 ~ 19 제외)
    avg_body_size = sum(k.body_size for k in klines) / Decimal(20)

    if klines[-1].is_bearish and klines[-1].body_size > avg_body_size:
        logger.info(
            f"직전 캔들 하락({klines[1].change_rate:.2f}% ↓) + 몸통길이 {klines[-2].body_size} > 20개평균 {avg_body_size}, 매수 점검"
        )

        try:
            bid_price = Decimal(ticker["data"][0]["bidPr"])  # 최우선 매수호가

            tick, qty_step, min_trade_num, min_trade_usdt = _calc_tick_and_steps()

            # size: ENTRY_AMOUNT / price → step 내림 + 최소수량 보정
            raw_qty = ENTRY_AMOUNT / bid_price
            qty = _round_to_step(raw_qty, qty_step)
            if qty < min_trade_num:
                qty = min_trade_num

            # 가격: tick 내림 정렬
            price = _round_to_step(bid_price, tick)
            tp = _round_to_step(price * Decimal("1.05"), tick)

            # 최소 주문 금액(USDT) 보정: notional >= min_trade_usdt
            if price * qty < min_trade_usdt:
                # 한 스텝 올려봄
                qty = _round_to_step(min_trade_usdt / price, qty_step)
                if qty < min_trade_num:
                    qty = min_trade_num

            res = await trade_client.place_order(
                symbol=SYMBOL,
                product_type="USDT-FUTURES",
                size=qty,
                price=bid_price,
                side="buy",
                order_type="limit",
                # preset_tp_price=tp,  # 5% TP, tick 정렬 완료
            )
            logger.info(f"매수 주문 결과: {res}")
        except BitgetError as e:
            if e.code == BitgetErrorCode.INSUFFICIENT_BALANCE:
                logger.warning(f"잔고 부족으로 매수 실패: {e}")
            else:
                logger.error(f"매수 주문 중 오류 발생: {e}")
                return

    # 직전 캔들이 상승이면 매도 ���검
    elif klines[-1].is_bullish:
        logger.info(f"직전 캔들 상승({klines[-1].change_rate:.2f}% ↑), 매도 점검")
        async with position_client as position_client:
            positions: list[dict] = await position_client.get_position(
                symbol=SYMBOL, product_type="USDT-FUTURES"
            )
            if not positions:
                logger.info("포지션 없음, 대기")
                return

            position = positions[0]

            avg_price = Decimal(position["openPriceAvg"])
            size = Decimal(position["available"])

            # 최우선 매도호가
            ask_price = Decimal(ticker["data"][0]["askPr"])

            # 최근 20개 캔들 평균 변동율 (퍼센트)
            avg_change_rate_20 = sum(k.change_rate for k in klines[-20:]) / Decimal(20)
            # 현재 기대 수익 변동율 (퍼센트)
            current_gain_rate = (ask_price - avg_price) / avg_price * Decimal(100)

            # 현재 변동율이 최근 20개 평균 변동율 이상일 때 부분 청산
            if size > 0 and current_gain_rate >= avg_change_rate_20:
                logger.info(
                    f"수익 실현 조건 충족: 현재수익률 {current_gain_rate:.4f}% >= 20개평균변동율 {avg_change_rate_20:.4f}%"
                )
                # 반익절 (50%) 수행: 포지션 방향 따라 hold_side 지정
                tick, qty_step, min_trade_num, min_trade_usdt = _calc_tick_and_steps()
                res = await trade_client.partial_close_position(
                    symbol=SYMBOL,
                    product_type="USDT-FUTURES",
                    hold_side=position.get("holdSide", "long"),
                    fraction=0.5,
                    order_type="market",
                    size_step=qty_step,
                    min_size=min_trade_num,
                )
                logger.info(f"부분 청산(50%) 결과: {res}")
            else:
                logger.info(
                    f"매도 조건 미충족 (현재수익률 {current_gain_rate:.4f}% < 평균변동율 {avg_change_rate_20:.4f}%), 대기"
                )

    else:
        logger.info("전일 변동 없음(어제 종가 == 그제 종가), 대기")

    logger.info(res)


if __name__ == "__main__":
    container = Container()
    container.init_resources()
    container.wire(modules=[__name__])

    asyncio.run(main())
