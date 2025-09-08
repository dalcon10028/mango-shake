import asyncio
import logging

from decimal import Decimal, ROUND_DOWN
from dependency_injector.wiring import inject, Provide
from exchange.bitget import BitgetFutureMarketClient, BitgetFutureTradeClient
from exchange.bitget.dto.bitget_error import BitgetError, BitgetErrorCode
from exchange.bitget.future.future_position_client import BitgetFuturePositionClient
from shared.containers import Container

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

ENTRY_AMOUNT = Decimal("100")
SYMBOL = "BTCUSDT"


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

    # async with market_client as market_client:
    # 최근 3개 4시간봉 조회 (현재 진행 중인 봉 제외)
    klines = await market_client.get_klines(symbol=SYMBOL, granularity="4H", limit=2)
    if len(klines) < 2:
        logger.error(f"Kline 데이터가 부족합니다: {len(klines)}")
        return

    yesterday = klines[1]
    day_before = klines[0]

    today_open = Decimal(yesterday[4])  # 오늘 시가 == 어제 종가
    prev_close = Decimal(yesterday[4])  # 어제 종가
    prev2_close = Decimal(day_before[4])  # 그제 종가

    # - 매수: 어제 종가 < 그제 종가 → 어제 종가에 지정가 매수 시도
    # - 매도: 어제 종가 > 그제 종가 AND 오늘 시가 ≥ 평단×1.05 → 전량 매도
    if prev_close < prev2_close:
        logger.info(
            f"전일 하락(어제 종가 {prev_close} < 그제 종가 {prev2_close}), 매수 시도"
        )
        # 종가랑 현재가 중 더 낮은 가격에 매수 주문

        try:
            ticker = await market_client.ticker(SYMBOL)
            bid_price = Decimal(ticker["data"][0]["bidPr"])  # 최우선 매수호가

            tick, qty_step, min_trade_num, min_trade_usdt = _calc_tick_and_steps()

            # size: ENTRY_AMOUNT / price → step 내림 + 최소수량 보정
            raw_qty = ENTRY_AMOUNT / prev_close
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
                preset_tp_price=tp,  # 5% TP, tick 정렬 완료
            )
            logger.info(f"매수 주문 결과: {res}")
        except BitgetError as e:
            if e.code == BitgetErrorCode.INSUFFICIENT_BALANCE:
                logger.warning(f"잔고 부족으로 매수 실패: {e}")
            else:
                logger.error(f"매수 주문 중 오류 발생: {e}")
                return

    elif prev_close > prev2_close:
        logger.info(
            f"전일 상승(어제 종가 {prev_close} > 그제 종가 {prev2_close}), 매도 점검"
        )
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
            if size > 0 and today_open >= avg_price * Decimal("1.05"):
                logger.info(
                    f"수익 실현 조건 충족: 오늘 시가 {today_open} ≥ 평단×1.05 ({avg_price * Decimal('1.05')})"
                )
                res = await trade_client.flash_close_position(symbol=SYMBOL)
                logger.info(f"매도 주문 결과: {res}")
            else:
                logger.info("매도 조건 미충족, 대기")

    else:
        logger.info("전일 변동 없음(어제 종가 == 그제 종가), 대기")

    logger.info(res)


if __name__ == "__main__":
    container = Container()
    container.init_resources()
    container.wire(modules=[__name__])

    asyncio.run(main())
