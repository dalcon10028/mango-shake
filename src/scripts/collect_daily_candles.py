import asyncio
import logging
from decimal import Decimal
from reactivex.scheduler.eventloop import AsyncIOScheduler
from sqlalchemy.dialects.postgresql import insert
from datetime import datetime, date, timedelta
from datetime import datetime as _dt
from exchange.bitget import BitgetSpotMarketClient
from exchange.upbit import UpbitCrixClient
from model import DailyCandle
from service import get_by_market
from shared.db import get_db
from shared.utils import get_base_date
from shared.utils.iterable import chunks

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

async def collect_crypto_currencies(base_date: date):
    """
    Collect and store daily candle data for all crypto currencies on the given base_date.
    """
    # Use existing asyncio loop for RxPY scheduling
    loop = asyncio.get_running_loop()
    scheduler = AsyncIOScheduler(loop=loop)

    # 1. Get ticker symbols for crypto currencies
    tickers = await get_by_market("CRYPTO_CURRENCY")

    # 2. For each ticker, fetch daily candle and add to session
    candles = []

    async with BitgetSpotMarketClient() as client:
        for ticker_chunk in chunks(tickers, 10):
            logger.info("Fetching candles for tickers: %s", [ticker.symbol for ticker in ticker_chunk])
            # Fetch one-day candle for base_date
            responses = await asyncio.gather(
                *[
                    client.get_candlesticks(
                        symbol=f"{ticker.symbol}USDT",
                        granularity="1day",
                        start_time=int(_dt.combine(base_date, _dt.min.time()).timestamp() * 1000),
                        end_time=int(_dt.combine(base_date + timedelta(days=1), _dt.min.time()).timestamp() * 1000),
                        limit=1
                    )
                    for ticker in ticker_chunk
                ]
            )

            for ticker, response in zip(ticker_chunk, responses):
                if not response or "data" not in response or not response["data"]:
                    logger.warning("No data returned for %s on %s", ticker.symbol, base_date)
                    continue
                data = response["data"][0]
                candle = DailyCandle(
                    exchange="BITGET",
                    # timestamp to date conversion
                    base_date=datetime.fromtimestamp(int(data[0]) / 1000).date(),
                    symbol=f"{ticker.symbol}/USDT",
                    open=Decimal(data[1]),
                    high=Decimal(data[2]),
                    low=Decimal(data[3]),
                    close=Decimal(data[4]),
                    volume=Decimal(data[5]),
                )
                candles.append(candle)

    logger.info(f"[bitget] Collected {len(candles)} candles for base date {base_date}")

    async with UpbitCrixClient() as client:
        data = await client.get_daily_candles("USDT")
        for candle_data, index in data:
            kst_date = datetime.strptime(candle_data["candleDateTimeKst"], "%Y-%m-%dT%H:%M:%S%z").date()
            if kst_date > base_date:
                continue

            candles.append(DailyCandle(
                exchange="UPBIT",
                # parse 2025-08-13T09:00:00+09:00
                base_date=kst_date,
                symbol=f"USDT/KRW",
                open=Decimal(candle_data["openingPrice"]),
                high=Decimal(candle_data["highPrice"]),
                low=Decimal(candle_data["lowPrice"]),
                close=Decimal(candle_data["tradePrice"]),
                volume=Decimal(candle_data["candleAccTradeVolume"]),
            ))

    logger.info(f"[upbit] Collected {len(candles)} candles for base date {base_date}")


    # 3. Upsert all collected candles to the database
    if candles:
        async with get_db() as session:
            # Prepare list of dicts for core insert
            values = [
                {
                    "exchange": c.exchange,
                    "base_date": c.base_date,
                    "symbol": c.symbol,
                    "open": c.open,
                    "high": c.high,
                    "low": c.low,
                    "close": c.close,
                    "volume": c.volume,
                }
                for c in candles
            ]
            # Build core insert with ON CONFLICT DO UPDATE
            stmt = insert(DailyCandle).values(values)
            stmt = stmt.on_conflict_do_update(
                index_elements=["symbol", "base_date"],
                set_={
                    "open": stmt.excluded.open,
                    "high": stmt.excluded.high,
                    "low": stmt.excluded.low,
                    "close": stmt.excluded.close,
                    "volume": stmt.excluded.volume,
                },
            )
            await session.execute(stmt)
            await session.commit()
            logger.info(f"Upserted {len(candles)} candles into the database")
    else:
        logger.info("No candles to upsert")




if __name__ == "__main__":
    base_date = get_base_date()
    logging.info("Starting to collect crypto currencies for base date: %s", base_date)
    asyncio.run(collect_crypto_currencies(base_date))
    logger.info("Finished collecting crypto currencies")