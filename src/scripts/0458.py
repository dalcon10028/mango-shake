"""
Bitget 선물 거래 자동화 스크립트
- 1시간봉 캔들 분석을 통한 자동 매수/매도
- 조건: 음봉 패턴 매수, 상승 시 부분 청산
"""

import asyncio
import logging
from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN
from typing import List, Tuple

from dependency_injector.wiring import inject, Provide

from exchange.bitget import BitgetFutureMarketClient, BitgetFutureTradeClient
from exchange.bitget.dto.bitget_error import BitgetError, BitgetErrorCode
from exchange.bitget.future.future_position_client import BitgetFuturePositionClient
from shared.containers import Container

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# 거래 설정
ENTRY_AMOUNT = Decimal("400")  # 진입 금액 (USDT)
SYMBOL = "BTCUSDT"
PROFIT_TARGET_RATE = Decimal("1.05")  # 5% 수익 목표
PARTIAL_CLOSE_RATIO = Decimal("0.5")  # 50% 부분 청산
MIN_PROFIT_RATE = Decimal("0.3")  # 최소 수익률 0.3%


@dataclass(frozen=True)
class Candle:
    """캔들 데이터 클래스"""
    start_time: int
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal

    @property
    def is_bullish(self) -> bool:
        """상승 캔들 여부"""
        return self.close > self.open

    @property
    def is_bearish(self) -> bool:
        """하락 캔들 여부"""
        return self.close < self.open

    @property
    def body_size(self) -> Decimal:
        """캔들 몸통 크기"""
        return abs(self.close - self.open)

    @property
    def change_rate(self) -> Decimal:
        """변동률 (%)"""
        if self.open == 0:
            return Decimal(0)
        return (self.close - self.open) / self.open * Decimal(100)


@dataclass(frozen=True)
class TradingSpecs:
    """거래 규격 정보"""
    tick: Decimal
    qty_step: Decimal
    min_trade_num: Decimal
    min_trade_usdt: Decimal


class BitgetTradingStrategy:
    """Bitget 거래 전략 클래스"""
    
    def __init__(
        self,
        market_client: BitgetFutureMarketClient,
        position_client: BitgetFuturePositionClient,
        trade_client: BitgetFutureTradeClient,
    ):
        self.market_client = market_client
        self.position_client = position_client
        self.trade_client = trade_client
        self.specs = self._get_trading_specs()

    def _get_trading_specs(self) -> TradingSpecs:
        """거래 규격 정보 계산"""
        # 하드코딩된 스펙 (실제로는 API에서 가져와야 함)
        spec = {
            "symbol": "BTCUSDT",
            "pricePlace": "1",
            "priceEndStep": "1",
            "sizeMultiplier": "0.0001",
            "volumePlace": "4",
            "minTradeNum": "0.0001",
            "minTradeUSDT": "5"
        }

        price_place = int(spec.get("pricePlace", "1"))
        price_end_step = Decimal(str(spec.get("priceEndStep", "1")))
        tick = (Decimal(1) / (Decimal(10) ** price_place)) * price_end_step

        if spec.get("sizeMultiplier"):
            qty_step = Decimal(str(spec["sizeMultiplier"]))
        else:
            vp = int(spec.get("volumePlace", "4"))
            qty_step = Decimal(1) / (Decimal(10) ** vp)

        min_trade_num = Decimal(str(spec.get("minTradeNum", "0")))
        min_trade_usdt = Decimal(str(spec.get("minTradeUSDT", "0")))

        return TradingSpecs(tick, qty_step, min_trade_num, min_trade_usdt)

    def _round_to_step(self, value: Decimal, step: Decimal) -> Decimal:
        """스텝 단위로 내림"""
        if step == 0:
            return value
        return (value / step).to_integral_value(rounding=ROUND_DOWN) * step

    async def get_klines(self, limit: int = 20) -> List[Candle]:
        """최근 캔들 데이터 조회"""
        klines = await self.market_client.get_klines(
            symbol=SYMBOL, granularity="1H", limit=limit
        )
        return [
            Candle(
                start_time=k[0],
                open=Decimal(k[1]),
                high=Decimal(k[2]),
                low=Decimal(k[3]),
                close=Decimal(k[4]),
                volume=Decimal(k[5]),
            )
            for k in klines
        ]

    async def get_ticker_price(self) -> Tuple[Decimal, Decimal]:
        """현재 호가 조회 (bid_price, ask_price)"""
        ticker = await self.market_client.ticker(SYMBOL)
        bid_price = Decimal(ticker["data"][0]["bidPr"])
        ask_price = Decimal(ticker["data"][0]["askPr"])
        return bid_price, ask_price

    def check_buy_conditions(self, candles: List[Candle]) -> bool:
        """매수 조건 검사"""
        if len(candles) < 3:
            return False

        avg_body_size = sum(k.body_size for k in candles) / Decimal(len(candles))

        # 조건 1: 전전 양봉 -> 직전 음봉, 직전 음봉 몸통 > 평균
        condition1 = (
            candles[-2].is_bullish
            and candles[-1].is_bearish
            and candles[-1].body_size > avg_body_size
        )

        # 조건 2: 연속 음봉, 직전 음봉 몸통이 더 크고 평균보다 큼
        condition2 = (
            candles[-2].is_bearish
            and candles[-1].is_bearish
            and candles[-1].body_size > avg_body_size
            and candles[-1].body_size > candles[-2].body_size
        )

        if condition1:
            logger.info(
                f"매수 조건 1 충족: 전전 양봉, 직전 음봉(몸통: {candles[-1].body_size} > 평균: {avg_body_size:.4f})"
            )
            return True
        elif condition2:
            logger.info(
                f"매수 조건 2 충족: 연속 음봉, 직전 음봉(몸통: {candles[-1].body_size}) > 전전 음봉(몸통: {candles[-2].body_size}) 및 평균({avg_body_size:.4f}) 이상"
            )
            return True

        return False

    async def place_buy_order(self, bid_price: Decimal) -> bool:
        """매수 주문 실행"""
        try:
            # 수량 계산
            raw_qty = ENTRY_AMOUNT / bid_price
            qty = self._round_to_step(raw_qty, self.specs.qty_step)
            if qty < self.specs.min_trade_num:
                qty = self.specs.min_trade_num

            # 가격 계산
            price = self._round_to_step(bid_price, self.specs.tick)

            # 최소 주문 금액 보정
            if price * qty < self.specs.min_trade_usdt:
                qty = self._round_to_step(self.specs.min_trade_usdt / price, self.specs.qty_step)
                if qty < self.specs.min_trade_num:
                    qty = self.specs.min_trade_num

            result = await self.trade_client.place_order(
                symbol=SYMBOL,
                product_type="USDT-FUTURES",
                size=qty,
                price=price,
                side="buy",
                trade_side="open",
                order_type="limit",
            )
            logger.info(f"매수 주문 결과: {result}")
            return True

        except BitgetError as e:
            if e.code == BitgetErrorCode.INSUFFICIENT_BALANCE:
                logger.warning(f"잔고 부족으로 매수 실패: {e}")
            else:
                logger.error(f"매수 주문 중 오류 발생: {e}")
            return False

    async def check_sell_conditions(self, candles: List[Candle], ask_price: Decimal) -> bool:
        """매도 조건 검사 및 실행"""
        async with self.position_client as client:
            positions = await client.get_position(
                symbol=SYMBOL, product_type="USDT-FUTURES"
            )

        if not positions:
            logger.info("포지션 없음, 대기")
            return False

        position = positions[0]
        logger.info(f"현재 포지션: {position}")

        avg_price = Decimal(position["openPriceAvg"])
        size = Decimal(position["available"])

        if size <= 0:
            return False

        # 수익률 계산
        avg_change_rate = sum(k.change_rate for k in candles[-20:]) / Decimal(20)
        current_gain_rate = (ask_price - avg_price) / avg_price * Decimal(100)

        # 매도 조건: 현재 수익률이 평균 변동률 이상이고 최소 수익률 이상
        if current_gain_rate >= avg_change_rate and current_gain_rate >= MIN_PROFIT_RATE:
            logger.info(
                f"수익 실현 조건 충족: 현재수익률 {current_gain_rate:.4f}% >= "
                f"20개평균변동율 {avg_change_rate:.4f}% and {current_gain_rate:.4f}% >= {MIN_PROFIT_RATE}%, "
                f"부분 청산({PARTIAL_CLOSE_RATIO * 100}%) 수행"
            )
            return await self._execute_partial_close(position, ask_price, size)
        else:
            logger.info(
                f"매도 조건 미충족 (현재수익률 {current_gain_rate:.4f}% < 평균변동율 {avg_change_rate:.4f}%), 대기"
            )
            return False

    async def _execute_partial_close(self, position: dict, ask_price: Decimal, size: Decimal) -> bool:
        """부분 청산 실행"""
        try:
            margin_mode = (position.get("marginMode") or "crossed").lower()
            hold_side = (position.get("holdSide") or "long").lower()
            limit_price = self._round_to_step(ask_price, self.specs.tick)
            close_size = self._round_to_step(size * PARTIAL_CLOSE_RATIO, self.specs.qty_step)

            result = await self.trade_client.place_order(
                symbol=SYMBOL,
                product_type="USDT-FUTURES",
                size=close_size,
                order_type="limit",
                side="sell",
                price=limit_price,
                trade_side="close",
                hold_side=hold_side,
                margin_mode=margin_mode,
            )
            logger.info(f"부분 청산({PARTIAL_CLOSE_RATIO * 100}%) 결과: {result}")
            return True

        except BitgetError as e:
            logger.error(f"부분 청산 중 오류 발생: {e}")
            return False

    async def cancel_all_orders(self) -> bool:
        """모든 주문 취소"""
        try:
            result = await self.trade_client.cancel_all_orders()
            logger.info(f"모든 주문 취소 결과: {result}")
            return True
        except BitgetError as e:
            if e.code == BitgetErrorCode.NO_ORDER_TO_CANCEL:
                logger.info("대기 주문 없음, 건너뜀")
                return True
            else:
                logger.error(f"주문 취소 중 오류 발생: {e}")
                return False

    async def execute_strategy(self):
        """전략 실행"""
        # 1. 모든 주문 취소
        if not await self.cancel_all_orders():
            return

        # 2. 캔들 데이터 및 호가 조회
        candles = await self.get_klines()
        if len(candles) < 3:
            logger.error(f"Kline 데이터가 부족합니다: {len(candles)}")
            return

        bid_price, ask_price = await self.get_ticker_price()

        # 3. 매수 조건 검사
        if self.check_buy_conditions(candles):
            await self.place_buy_order(bid_price)
        # 4. 매도 조건 검사 (상승 캔들인 경우)
        elif candles[-1].is_bullish:
            logger.info(f"직전 캔들 상승({candles[-1].change_rate:.2f}% ↑), 매도 점검")
            await self.check_sell_conditions(candles, ask_price)
        else:
            logger.info(f"조건 미충족, 대기 (직전 캔들 변동률: {candles[-1].change_rate:.2f}%)")


@inject
async def main(
    market_client: BitgetFutureMarketClient = Provide[Container.bitget_future_market_client],
    position_client: BitgetFuturePositionClient = Provide[Container.bitget_future_position_client],
    trade_client: BitgetFutureTradeClient = Provide[Container.bitget_future_trade_client],
):
    """메인 실행 함수"""
    strategy = BitgetTradingStrategy(market_client, position_client, trade_client)
    await strategy.execute_strategy()


if __name__ == "__main__":
    container = Container()
    container.init_resources()
    container.wire(modules=[__name__])

    asyncio.run(main())
