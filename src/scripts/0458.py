import asyncio
import logging

from decimal import Decimal
from dependency_injector.wiring import inject, Provide

from exchange.bitget import BitgetFutureMarketClient, BitgetFutureTradeClient
from exchange.bitget.dto.bitget_error import BitgetError, BitgetErrorCode
from exchange.bitget.future.future_position_client import BitgetFuturePositionClient
from shared.containers import Container

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

ENTRY_AMOUNT = Decimal("200")
SYMBOL = "BTCUSDT"

@inject
async def main(
    market_client: BitgetFutureMarketClient = Provide[Container.bitget_future_market_client],
    position_client: BitgetFuturePositionClient = Provide[Container.bitget_future_position_client],
    trade_client: BitgetFutureTradeClient = Provide[Container.bitget_future_trade_client],
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

    async with market_client as market_client:
        # 최근 3개 일봉: [오늘, 어제, 그제] 순으로 온다고 가정
        klines = await market_client.get_klines(
            symbol=SYMBOL,
            granularity="1Dutc",
            limit=2
        )
        if len(klines) < 2:
            logger.error(f"Kline 데이터가 부족합니다: {len(klines)}")
            return

        yesterday = klines[1]
        day_before = klines[0]

        today_open = Decimal(yesterday[4])       # 오늘 시가 == 어제 종가
        prev_close = Decimal(yesterday[4])   # 어제 종가
        prev2_close = Decimal(day_before[4]) # 그제 종가


    # - 매수: 어제 종가 < 그제 종가 → 어제 종가에 지정가 매수 시도
    # - 매도: 어제 종가 > 그제 종가 AND 오늘 시가 ≥ 평단×1.05 → 전량 매도
    if prev_close < prev2_close:
        logger.info(f"전일 하락(어제 종가 {prev_close} < 그제 종가 {prev2_close}), 매수 시도")
        # 종가랑 현재가 중 더 낮은 가격에 매수 주문

        async with trade_client as trade_client:
            try:
                res = await trade_client.place_order(
                    symbol=SYMBOL,
                    product_type="USDT-FUTURES",
                    size=ENTRY_AMOUNT / prev_close,
                    price=prev_close,
                    side="buy",
                    order_type="limit",
                )
                logger.info(f"매수 주문 결과: {res}")
            except BitgetError as e:
                if e.code == BitgetErrorCode.INSUFFICIENT_BALANCE:
                    logger.warning(f"잔고 부족으로 매수 실패: {e}")
                else:
                    logger.error(f"매수 주문 중 오류 발생: {e}")
                    return

    elif prev_close > prev2_close:
        logger.info(f"전일 상승(어제 종가 {prev_close} > 그제 종가 {prev2_close}), 매도 점검")
        async with position_client as position_client:
            positions: list[dict] = await position_client.get_position(symbol=SYMBOL, product_type="USDT-FUTURES")
            if not positions:
                logger.info("포지션 없음, 대기")
                return

            position = positions[0]

            avg_price = Decimal(position['openPriceAvg'])
            size = Decimal(position['available'])
            if size > 0 and today_open >= avg_price * Decimal("1.05"):
                logger.info(f"수익 실현 조건 충족: 오늘 시가 {today_open} ≥ 평단×1.05 ({avg_price * Decimal('1.05')})")
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