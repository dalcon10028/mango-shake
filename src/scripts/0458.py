import asyncio
import logging
import uuid
from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN
from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime

from dependency_injector.wiring import inject, Provide

from exchange.bitget import BitgetFutureMarketClient, BitgetFutureTradeClient
from exchange.bitget.dto.bitget_error import BitgetError, BitgetErrorCode
from exchange.bitget.future.future_position_client import BitgetFuturePositionClient
from exchange.bitget.future.future_account_client import BitgetFutureAccountClient
from shared.containers import Container
from shared.settings import get_settings

logger = logging.getLogger(__name__)

# 상수 정의
class TradingConstants:
    """거래 관련 상수"""
    POSITION_RATIO_HIGH_THRESHOLD = Decimal("50")  # 50%
    POSITION_RATIO_MID_THRESHOLD = Decimal("40")   # 40%
    ROE_HIGH_THRESHOLD = Decimal("-30")            # -30%
    ROE_MID_THRESHOLD = Decimal("-20")             # -20%
    MIN_CANDLES_REQUIRED = 3
    KLINE_LIMIT = 20
    GRANULARITY = "1H"
    PRODUCT_TYPE = "USDT-FUTURES"


@dataclass(frozen=True)
class TradingConfig:
    """거래 설정 데이터 클래스"""
    symbol: str
    profit_target_rate: Decimal
    partial_close_ratio: Decimal
    min_profit_rate: Decimal
    division_count: int

    @classmethod
    def from_settings(cls) -> 'TradingConfig':
        """설정에서 거래 설정 로드"""
        settings = get_settings()
        trading_config = settings.strategy_0458
        
        return cls(
            symbol=trading_config.symbol,
            profit_target_rate=Decimal(str(trading_config.profit_target_rate)),
            partial_close_ratio=Decimal(str(trading_config.partial_close_ratio)),
            min_profit_rate=Decimal(str(trading_config.min_profit_rate)),
            division_count=trading_config.division_count
        )


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

    def __str__(self) -> str:
        """캔들 정보를 읽기 쉬운 형태로 표시"""
        direction = "↑" if self.is_bullish else "↓"
        return f"Candle({direction} {self.change_rate:.2f}%, O:{self.open} H:{self.high} L:{self.low} C:{self.close})"


@dataclass(frozen=True)
class TradingSpecs:
    """거래 규격 정보"""
    tick: Decimal
    qty_step: Decimal
    min_trade_num: Decimal
    min_trade_usdt: Decimal


@dataclass(frozen=True)
class PositionInfo:
    """포지션 정보 데이터 클래스"""
    position_value_usdt: Decimal
    roe_percentage: Decimal
    size: Decimal
    margin: Decimal
    unrealized_pnl: Decimal
    position_data: Dict[str, Any]

    @property
    def has_position(self) -> bool:
        """포지션 보유 여부"""
        return self.size > 0

    def __str__(self) -> str:
        """포지션 정보를 읽기 쉬운 형태로 표시"""
        return f"Position(Size:{self.size}, Value:{self.position_value_usdt}USDT, ROE:{self.roe_percentage:.2f}%, PnL:{self.unrealized_pnl})"


@dataclass(frozen=True)
class TradingDecision:
    """거래 결정 정보"""
    action: str  # "BUY", "SELL", "WAIT"
    reason: str
    candle_pattern: Optional[str] = None
    position_info: Optional[PositionInfo] = None
    execution_id: Optional[str] = None

    def __post_init__(self):
        """실행 ID 자동 생성"""
        if self.execution_id is None:
            object.__setattr__(self, 'execution_id', str(uuid.uuid4())[:8])


class BitgetTradingStrategy:
    """Bitget 거래 전략 클래스"""
    
    def __init__(
        self,
        market_client: BitgetFutureMarketClient,
        position_client: BitgetFuturePositionClient,
        trade_client: BitgetFutureTradeClient,
        account_client: BitgetFutureAccountClient,
    ):
        self.market_client = market_client
        self.position_client = position_client
        self.trade_client = trade_client
        self.account_client = account_client
        self.config = TradingConfig.from_settings()
        self.specs = self._get_trading_specs()
        
        logger.info(f"전략 초기화 완료 - {self.config}")

    def _get_trading_specs(self) -> TradingSpecs:
        """거래 규격 정보 계산"""
        # TODO: API에서 실제 스펙을 가져오도록 개선 필요
        spec = {
            "symbol": self.config.symbol,
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

        specs = TradingSpecs(tick, qty_step, min_trade_num, min_trade_usdt)
        logger.debug(f"거래 규격 정보: {specs}")
        return specs

    async def get_account_equity(self) -> Decimal:
        """전체 평가금액 조회"""
        try:
            async with self.account_client as client:
                account = await client.get_accounts(product_type=TradingConstants.PRODUCT_TYPE)
            
            if not account:
                raise ValueError("계좌 정보를 찾을 수 없습니다")
            
            equity = Decimal(str(account.get("accountEquity", "0")))
            logger.debug(f"계좌 평가금액: {equity} USDT")
            return equity
            
        except Exception as e:
            logger.error(f"계좌 정보 조회 실패: {e}")
            raise

    async def get_leverage(self) -> Decimal:
        """현재 심볼의 레버리지 설정 조회"""
        try:
            async with self.account_client as client:
                leverage_info = await client.get_leverage(
                    symbol=self.config.symbol,
                    product_type=TradingConstants.PRODUCT_TYPE
                )
            
            if not leverage_info:
                logger.warning(f"레버리지 정보를 찾을 수 없습니다. 기본값 1배 사용")
                return Decimal("1")
            
            leverage = Decimal(str(leverage_info.get("leverage", "1")))
            logger.debug(f"현재 레버리지: {leverage}배")
            return leverage
            
        except Exception as e:
            logger.warning(f"레버리지 조회 실패, 기본값 1배 사용: {e}")
            return Decimal("1")

    async def calculate_entry_amount(self) -> Decimal:
        """분할 투자 + 레버리지를 반영한 진입금액 계산"""
        try:
            total_equity = await self.get_account_equity()
            leverage = await self.get_leverage()
            
            entry_amount = (total_equity / Decimal(self.config.division_count)) * leverage
            
            logger.info(
                f"진입금액 계산: 총자산({total_equity}) / 분할수({self.config.division_count}) * 레버리지({leverage}배) = {entry_amount} USDT"
            )
            
            return entry_amount
            
        except Exception as e:
            logger.error(f"진입금액 계산 실패: {e}")
            raise

    async def get_current_position_info(self) -> PositionInfo:
        """현재 포지션 정보 조회"""
        try:
            async with self.position_client as client:
                positions = await client.get_position(
                    symbol=self.config.symbol, 
                    product_type=TradingConstants.PRODUCT_TYPE
                )
            
            if not positions:
                return PositionInfo(
                    position_value_usdt=Decimal("0"),
                    roe_percentage=Decimal("0"),
                    size=Decimal("0"),
                    margin=Decimal("0"),
                    unrealized_pnl=Decimal("0"),
                    position_data={}
                )
            
            position = positions[0]
            
            position_size = Decimal(position.get("total", "0"))
            mark_price = Decimal(position.get("markPrice", "0"))
            position_value_usdt = position_size * mark_price
            
            unrealized_pnl = Decimal(position.get("unrealizedPL", "0"))
            margin = Decimal(position.get("margin", "0"))
            
            roe_percentage = (unrealized_pnl / margin * Decimal(100)) if margin > 0 else Decimal(0)
            
            pos_info = PositionInfo(
                position_value_usdt=position_value_usdt,
                roe_percentage=roe_percentage,
                size=position_size,
                margin=margin,
                unrealized_pnl=unrealized_pnl,
                position_data=position
            )
            
            logger.debug(f"포지션 정보: {pos_info}")
            return pos_info
            
        except Exception as e:
            logger.error(f"포지션 정보 조회 실패: {e}")
            raise

    async def check_position_entry_conditions(self, position_info: PositionInfo, total_equity: Decimal) -> Tuple[bool, str]:
        """포지션 기반 추가 진입 조건 검사"""
        if not position_info.has_position:
            return True, "포지션 없음 - 진입 가능"
        
        position_ratio = (position_info.position_value_usdt / total_equity) * Decimal(100)
        roe = position_info.roe_percentage
        
        logger.info(
            f"포지션 분석: 비율({position_ratio:.2f}%), ROE({roe:.2f}%), "
            f"포지션가치({position_info.position_value_usdt} USDT), 총자산({total_equity} USDT)"
        )
        
        if position_ratio >= TradingConstants.POSITION_RATIO_HIGH_THRESHOLD:
            if roe <= TradingConstants.ROE_HIGH_THRESHOLD:
                reason = f"고비율 포지션({position_ratio:.2f}% >= 50%) + 깊은 손실(ROE {roe:.2f}% <= -30%) - 추가 진입 허용"
                return True, reason
            else:
                reason = f"고비율 포지션({position_ratio:.2f}% >= 50%) 이지만 ROE({roe:.2f}% > -30%) 부족 - 진입 금지"
                return False, reason
                
        elif position_ratio >= TradingConstants.POSITION_RATIO_MID_THRESHOLD:
            if roe <= TradingConstants.ROE_MID_THRESHOLD:
                reason = f"중비율 포지션({position_ratio:.2f}% >= 40%) + 손실(ROE {roe:.2f}% <= -20%) - 추가 진입 허용"
                return True, reason
            else:
                reason = f"중비율 포지션({position_ratio:.2f}% >= 40%) 이지만 ROE({roe:.2f}% > -20%) 부족 - 진입 금지"
                return False, reason
        else:
            reason = f"저비율 포지션({position_ratio:.2f}% < 40%) - 자유 진입 가능"
            return True, reason

    def _round_to_step(self, value: Decimal, step: Decimal) -> Decimal:
        """스텝 단위로 내림"""
        if step == 0:
            return value
        return (value / step).to_integral_value(rounding=ROUND_DOWN) * step

    async def get_klines(self, limit: int = TradingConstants.KLINE_LIMIT) -> List[Candle]:
        """최근 캔들 데이터 조회"""
        try:
            klines = await self.market_client.get_klines(
                symbol=self.config.symbol, 
                granularity=TradingConstants.GRANULARITY, 
                limit=limit
            )
            
            candles = [
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
            
            logger.debug(f"캔들 데이터 조회 완료: {len(candles)}개, 최신캔들: {candles[-1] if candles else 'None'}")
            return candles
            
        except Exception as e:
            logger.error(f"캔들 데이터 조회 실패: {e}")
            raise

    async def get_ticker_price(self) -> Tuple[Decimal, Decimal]:
        """현재 호가 조회 (bid_price, ask_price)"""
        try:
            ticker = await self.market_client.ticker(self.config.symbol)
            bid_price = Decimal(ticker["data"][0]["bidPr"])
            ask_price = Decimal(ticker["data"][0]["askPr"])
            
            logger.debug(f"현재 호가: Bid({bid_price}), Ask({ask_price})")
            return bid_price, ask_price
            
        except Exception as e:
            logger.error(f"호가 조회 실패: {e}")
            raise

    def analyze_candle_patterns(self, candles: List[Candle]) -> Tuple[bool, str]:
        """캔들 패턴 분석"""
        if len(candles) < TradingConstants.MIN_CANDLES_REQUIRED:
            return False, f"캔들 데이터 부족 ({len(candles)}/{TradingConstants.MIN_CANDLES_REQUIRED})"

        avg_body_size = sum(k.body_size for k in candles) / Decimal(len(candles))

        # 패턴 1: 전전 양봉 -> 직전 음봉 (직전 음봉 몸통 > 평균)
        if (candles[-2].is_bullish and candles[-1].is_bearish and 
            candles[-1].body_size > avg_body_size):
            pattern_desc = (f"패턴1: 전전양봉→직전음봉 "
                           f"(음봉몸통:{candles[-1].body_size:.4f} > 평균:{avg_body_size:.4f})")
            logger.info(f"매수 패턴 감지 - {pattern_desc}")
            return True, pattern_desc

        # 패턴 2: 연속 음봉 (직전 음봉 몸통이 더 크고 평균 이상)
        if (candles[-2].is_bearish and candles[-1].is_bearish and 
            candles[-1].body_size > avg_body_size and 
            candles[-1].body_size > candles[-2].body_size):
            pattern_desc = (f"패턴2: 연속음봉확대 "
                           f"(직전:{candles[-1].body_size:.4f} > 전전:{candles[-2].body_size:.4f} > 평균:{avg_body_size:.4f})")
            logger.info(f"매수 패턴 감지 - {pattern_desc}")
            return True, pattern_desc

        return False, "매수 패턴 없음"

    async def make_trading_decision(self, candles: List[Candle]) -> TradingDecision:
        """거래 결정 로직"""
        execution_id = str(uuid.uuid4())[:8]
        logger.info(f"[{execution_id}] 거래 결정 분석 시작")

        # 1. 캔들 패턴 분석
        pattern_matched, pattern_reason = self.analyze_candle_patterns(candles)
        
        if not pattern_matched:
            decision = TradingDecision(
                action="WAIT",
                reason=pattern_reason,
                execution_id=execution_id
            )
            logger.info(f"[{execution_id}] 거래 결정: {decision.action} - {decision.reason}")
            return decision

        # 2. 포지션 조건 검사
        try:
            position_info = await self.get_current_position_info()
            total_equity = await self.get_account_equity()
            
            entry_allowed, position_reason = await self.check_position_entry_conditions(position_info, total_equity)
            
            if not entry_allowed:
                decision = TradingDecision(
                    action="WAIT",
                    reason=f"캔들패턴 충족하지만 포지션 제한: {position_reason}",
                    candle_pattern=pattern_reason,
                    position_info=position_info,
                    execution_id=execution_id
                )
                logger.warning(f"[{execution_id}] 거래 결정: {decision.action} - {decision.reason}")
                return decision

            # 3. 매수 결정
            decision = TradingDecision(
                action="BUY",
                reason=f"매수조건 충족: {pattern_reason} + {position_reason}",
                candle_pattern=pattern_reason,
                position_info=position_info,
                execution_id=execution_id
            )
            logger.info(f"[{execution_id}] 거래 결정: {decision.action} - {decision.reason}")
            return decision

        except Exception as e:
            decision = TradingDecision(
                action="WAIT",
                reason=f"거래 결정 분석 실패: {e}",
                execution_id=execution_id
            )
            logger.error(f"[{execution_id}] 거래 결정: {decision.action} - {decision.reason}")
            return decision

    async def execute_buy_order(self, bid_price: Decimal, decision: TradingDecision) -> bool:
        """매수 주문 실행"""
        try:
            entry_amount = await self.calculate_entry_amount()
            
            # 수량 계산
            raw_qty = entry_amount / bid_price
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

            logger.info(
                f"[{decision.execution_id}] 매수 주문 실행: "
                f"Symbol({self.config.symbol}), Price({price}), Qty({qty}), "
                f"EntryAmount({entry_amount}), Reason({decision.reason})"
            )

            result = await self.trade_client.place_order(
                symbol=self.config.symbol,
                product_type=TradingConstants.PRODUCT_TYPE,
                size=qty,
                price=price,
                side="buy",
                trade_side="open",
                order_type="limit",
            )
            
            logger.info(f"[{decision.execution_id}] 매수 주문 성공: {result}")
            return True

        except BitgetError as e:
            if e.code == BitgetErrorCode.INSUFFICIENT_BALANCE:
                logger.warning(f"[{decision.execution_id}] 잔고 부족으로 매수 실패: {e}")
            else:
                logger.error(f"[{decision.execution_id}] 매수 주문 중 오류 발생: {e}")
            return False
        except Exception as e:
            logger.error(f"[{decision.execution_id}] 매수 주문 예외 발생: {e}")
            return False

    async def check_sell_conditions(self, candles: List[Candle], ask_price: Decimal) -> bool:
        """매도 조건 검사 및 실행"""
        execution_id = str(uuid.uuid4())[:8]
        
        try:
            position_info = await self.get_current_position_info()

            if not position_info.has_position:
                logger.debug(f"[{execution_id}] 포지션 없음, 매도 검사 건너뜀")
                return False

            logger.info(f"[{execution_id}] 매도 조건 검사 시작: {position_info}")

            avg_price = Decimal(position_info.position_data["openPriceAvg"])
            size = Decimal(position_info.position_data["available"])

            if size <= 0:
                logger.debug(f"[{execution_id}] 청산 가능한 포지션 크기 없음: {size}")
                return False

            # 수익률 계산
            avg_change_rate = sum(k.change_rate for k in candles[-20:]) / Decimal(20)
            current_gain_rate = (ask_price - avg_price) / avg_price * Decimal(100)

            logger.info(
                f"[{execution_id}] 수익률 분석: 현재수익률({current_gain_rate:.4f}%), "
                f"20개평균변동률({avg_change_rate:.4f}%), 최소수익률({self.config.min_profit_rate}%)"
            )

            # 매도 조건: 현재 수익률이 평균 변동률 이상이고 최소 수익률 이상
            if current_gain_rate >= avg_change_rate and current_gain_rate >= self.config.min_profit_rate:
                reason = (f"수익실현 조건충족: 현재수익률({current_gain_rate:.4f}%) >= "
                         f"평균변동률({avg_change_rate:.4f}%) && >= 최소수익률({self.config.min_profit_rate}%)")
                logger.info(f"[{execution_id}] {reason}")
                return await self._execute_partial_close(position_info.position_data, ask_price, size, execution_id)
            else:
                logger.info(
                    f"[{execution_id}] 매도 조건 미충족: 현재수익률({current_gain_rate:.4f}%) < "
                    f"평균변동률({avg_change_rate:.4f}%) 또는 < 최소수익률({self.config.min_profit_rate}%)"
                )
                return False

        except Exception as e:
            logger.error(f"[{execution_id}] 매도 조건 검사 실패: {e}")
            return False

    async def _execute_partial_close(self, position: dict, ask_price: Decimal, size: Decimal, execution_id: str) -> bool:
        """부분 청산 실행"""
        try:
            margin_mode = (position.get("marginMode") or "crossed").lower()
            hold_side = (position.get("holdSide") or "long").lower()
            limit_price = self._round_to_step(ask_price, self.specs.tick)
            close_size = self._round_to_step(size * self.config.partial_close_ratio, self.specs.qty_step)

            logger.info(
                f"[{execution_id}] 부분 청산 실행: "
                f"Symbol({self.config.symbol}), Price({limit_price}), Size({close_size}), "
                f"Ratio({self.config.partial_close_ratio * 100}%), Mode({margin_mode}), Side({hold_side})"
            )

            result = await self.trade_client.place_order(
                symbol=self.config.symbol,
                product_type=TradingConstants.PRODUCT_TYPE,
                size=close_size,
                order_type="limit",
                side="sell",
                price=limit_price,
                trade_side="close",
                hold_side=hold_side,
                margin_mode=margin_mode,
            )
            
            logger.info(f"[{execution_id}] 부분 청산 성공: {result}")
            return True

        except BitgetError as e:
            logger.error(f"[{execution_id}] 부분 청산 중 오류 발생: {e}")
            return False
        except Exception as e:
            logger.error(f"[{execution_id}] 부분 청산 예외 발생: {e}")
            return False

    async def cancel_all_orders(self) -> bool:
        """모든 주문 취소"""
        execution_id = str(uuid.uuid4())[:8]
        
        try:
            logger.info(f"[{execution_id}] 모든 주문 취소 시작")
            result = await self.trade_client.cancel_all_orders()
            logger.info(f"[{execution_id}] 모든 주문 취소 성공: {result}")
            return True
            
        except BitgetError as e:
            if e.code == BitgetErrorCode.NO_ORDER_TO_CANCEL:
                logger.debug(f"[{execution_id}] 취소할 주문 없음")
                return True
            else:
                logger.error(f"[{execution_id}] 주문 취소 중 오류 발생: {e}")
                return False
        except Exception as e:
            logger.error(f"[{execution_id}] 주문 취소 예외 발생: {e}")
            return False

    async def execute_strategy(self):
        """전략 실행 - 메인 로직"""
        strategy_execution_id = str(uuid.uuid4())[:8]
        start_time = datetime.now()
        
        logger.info(f"[{strategy_execution_id}] === 전략 실행 시작 ({start_time}) ===")
        
        try:
            # 1. 모든 주문 취소
            if not await self.cancel_all_orders():
                logger.error(f"[{strategy_execution_id}] 주문 취소 실패로 전략 실행 중단")
                return

            # 2. 시장 데이터 조회
            logger.info(f"[{strategy_execution_id}] 시장 데이터 조회 중...")
            candles = await self.get_klines()
            
            if len(candles) < TradingConstants.MIN_CANDLES_REQUIRED:
                logger.error(f"[{strategy_execution_id}] 캔들 데이터 부족: {len(candles)}/{TradingConstants.MIN_CANDLES_REQUIRED}")
                return

            bid_price, ask_price = await self.get_ticker_price()
            
            logger.info(
                f"[{strategy_execution_id}] 시장 상황: "
                f"최신캔들({candles[-1]}), Bid({bid_price}), Ask({ask_price})"
            )

            # 3. 거래 결정 및 실행
            decision = await self.make_trading_decision(candles)
            
            if decision.action == "BUY":
                await self.execute_buy_order(bid_price, decision)
            elif candles[-1].is_bullish:
                logger.info(f"[{strategy_execution_id}] 상승 캔들 감지, 매도 조건 검사")
                await self.check_sell_conditions(candles, ask_price)
            else:
                logger.info(f"[{strategy_execution_id}] 대기: {decision.reason}")

        except Exception as e:
            logger.error(f"[{strategy_execution_id}] 전략 실행 중 예외 발생: {e}")
        finally:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            logger.info(f"[{strategy_execution_id}] === 전략 실행 완료 ({end_time}, 소요시간: {duration:.2f}초) ===")


@inject
async def main(
    market_client: BitgetFutureMarketClient = Provide[Container.bitget_future_market_client],
    position_client: BitgetFuturePositionClient = Provide[Container.bitget_future_position_client],
    trade_client: BitgetFutureTradeClient = Provide[Container.bitget_future_trade_client],
    account_client: BitgetFutureAccountClient = Provide[Container.bitget_future_account_client],
):
    """메인 실행 함수"""
    try:
        logger.info("=== 거래 봇 시작 ===")
        strategy = BitgetTradingStrategy(market_client, position_client, trade_client, account_client)
        await strategy.execute_strategy()
        logger.info("=== 거래 봇 완료 ===")
    except Exception as e:
        logger.error(f"메인 실행 중 오류 발생: {e}")
        raise


if __name__ == "__main__":
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    container = Container()
    container.init_resources()
    container.wire(modules=[__name__])

    asyncio.run(main())