import asyncio
import logging

from decimal import Decimal
from bitget.future import BitgetFutureMarketClient, BitgetFutureTradeClient
from bitget.future.future_position_client import BitgetFuturePositionClient
from dependency_injector.wiring import inject, Provide
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
    try:
        res = await trade_client.cancel_all_orders() # 모든 주문 취소
        logger.info(f"모든 주문 취소 결과: {res}")
    except Exception as e:
        if "No order to cancel" in str(e):
            logger.info("대기 주문 없음, 건너뜀")
        else:
            logger.error(f"주문 취소 중 오류 발생: {e}")
            return


    async with market_client as market_client:
        res = await market_client.get_klines(
            symbol=SYMBOL,
            granularity="1Dutc",
            limit=1
        )
        last_candle = res[0]
        open_price = Decimal(last_candle[1])
        # high_price = Decimal(last_candle[2])
        # low_price = Decimal(last_candle[3])
        close_price = Decimal(last_candle[4])

    # 전날이 음봉이면 매수
    if close_price < open_price:
        logger.info("전날 음봉, 매수")
        # 매수 로직 추가
        async with trade_client as trade_client:
            res = await trade_client.place_order(
                symbol=SYMBOL,
                product_type="USDT-FUTURES",
                size=ENTRY_AMOUNT / close_price,  # 수량은 USDT로 계산
                price=close_price,
                side="buy",
                order_type="limit",
            )
            logger.info(f"매수 주문 결과: {res}")

    elif close_price > open_price:
        logger.info("전날 양봉, 매도 또는 대기")
        # 포지션을 들고와서 평단가 대비 5% 이상 수익이면 매도
        async with position_client as position_client:
            position = await position_client.get_position(symbol=SYMBOL, product_type="USDT-FUTURES")
            if not position:
                logger.info("포지션 없음, 대기")
                return

            avg_price = Decimal(position['openPriceAvg'])
            size = Decimal(position['size'])
            if size > 0 and close_price >= avg_price * Decimal("1.05"):
                # 수익 실현
                logger.info("수익 실현, 매도")
                res = await trade_client.flash_close_position(symbol=SYMBOL)
                logger.info(f"매도 주문 결과: {res}")
            else:
                logger.info("포지션 유지 또는 손실, 대기")

    else:
        logger.info("전날 변동 없음, 대기")
    logger.info(res)



if __name__ == "__main__":
    container = Container()
    container.init_resources()
    container.wire(modules=[__name__])

    asyncio.run(main())