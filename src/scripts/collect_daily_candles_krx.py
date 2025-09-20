import asyncio
import logging
from datetime import date, timedelta, datetime
from decimal import Decimal, InvalidOperation
from typing import Optional, List

import argparse
from dependency_injector.wiring import inject, Provide
from sqlalchemy import select, distinct
from sqlalchemy.dialects.postgresql import insert

from exchange.kiwoom.rest_client import KiwoomRestClient
from model.condition_search_result import ConditionSearchResult
from model.daily_candle_krx import DailyCandleKrx
from shared.containers import Container
from shared.db import get_db

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def to_decimal(v: Optional[str]) -> Decimal:
    """Convert Kiwoom zero-padded numeric strings (or None/"") safely to Decimal."""
    if v is None or v == "":
        return Decimal(0)
    try:
        return Decimal(v)
    except (InvalidOperation, TypeError):
        return Decimal(0)


async def fetch_and_save_daily_candles(
    kiwoom_client: KiwoomRestClient, target_date: date, symbols: List[str]
):
    """지정된 날짜와 종목들에 대해 일별 캔들 데이터를 가져와 DB에 저장"""
    records = []
    
    for symbol in symbols:
        logger.info(f"Fetching daily candles for {symbol} on {target_date}")
        
        # Kiwoom API 호출하여 일별 주가 데이터 조회
        response = await kiwoom_client.get_daily_candles(
            symbol=symbol, date=target_date.strftime("%Y%m%d")
        )
        await asyncio.sleep(0.2)  # API rate limit

        if not response or not response.get("daly_stkpc"):
            logger.warning(f"No data returned for {symbol} on {target_date}")
            continue

        # API 응답에서 일별 주가 데이터 추출
        for item in response["daly_stkpc"]:
            records.append(
                {
                    "symbol": symbol,
                    "date": datetime.strptime(item["date"], "%Y%m%d").date(),
                    "open_price": to_decimal(item["open_pric"]),
                    "high_price": to_decimal(item["high_pric"]),
                    "low_price": to_decimal(item["low_pric"]),
                    "close_price": to_decimal(item["close_pric"]),
                    "price_change": to_decimal(item["pred_rt"]),
                    "fluctuation_rate": to_decimal(item["flu_rt"]),
                    "volume": to_decimal(item["trde_qty"]),
                    "trade_amount": to_decimal(item["amt_mn"]),
                    "credit_ratio": to_decimal(item["crd_rt"]),
                    "individual_trade_volume": to_decimal(item["ind"]),
                    "institution_trade_volume": to_decimal(item["orgn"]),
                    "foreign_trade_volume": to_decimal(item["for_qty"]),
                    "foreign_company_trade_volume": to_decimal(item["frgn"]),
                    "program_trade_volume": to_decimal(item["prm"]),
                    "foreign_ownership_ratio": to_decimal(item["for_rt"]),
                    "foreign_shares_held": to_decimal(item["for_poss"]),
                    "foreign_ownership_weight": to_decimal(item["for_wght"]),
                    "foreign_net_purchase": to_decimal(item["for_netprps"]),
                    "institution_net_purchase": to_decimal(item["orgn_netprps"]),
                    "individual_net_purchase": to_decimal(item["ind_netprps"]),
                    "credit_balance_ratio": to_decimal(item["crd_remn_rt"]),
                    "response": item,
                }
            )

    if not records:
        logger.info(f"No daily candle data to upsert for {target_date}")
        return

    # 데이터베이스에 Upsert (Insert or Update)
    async with get_db() as session:
        stmt = insert(DailyCandleKrx).values(records)
        stmt = stmt.on_conflict_do_update(
            index_elements=["symbol", "date"],
            set_={
                col: stmt.excluded[col]
                for col in records[0].keys()
                if col not in ("symbol", "date")
            },
        )
        await session.execute(stmt)
        await session.commit()
    
    logger.info(
        f"Upserted {len(records)} daily candles for {len(symbols)} symbols on {target_date}"
    )


@inject
async def main(
    start_date_str: str,
    end_date_str: str,
    kiwoom_rest_client: KiwoomRestClient = Provide[Container.kiwoom_rest_client],
):
    """메인 함수: 지정된 기간의 일별 캔들 데이터를 수집"""
    start_date = date.fromisoformat(start_date_str)
    end_date = date.fromisoformat(end_date_str)

    logger.info(f"Collecting daily candles from {start_date} to {end_date}")

    # 시작일부터 종료일까지 하루씩 처리
    delta = end_date - start_date
    for i in range(delta.days + 1):
        current_date = start_date + timedelta(days=i)
        logger.info(f"Processing date: {current_date}")

        # 해당 날짜의 condition_search_result에서 종목 목록 조회
        async with get_db() as session:
            result = await session.execute(
                select(distinct(ConditionSearchResult.symbol)).where(
                    ConditionSearchResult.base_date == current_date
                )
            )
            symbols = [row[0] for row in result.all()]

        if not symbols:
            logger.warning(f"No symbols found for date {current_date}. Skipping.")
            continue

        logger.info(f"Found {len(symbols)} symbols for {current_date}")
        
        # 해당 날짜의 종목들에 대해 일별 캔들 데이터 수집 및 저장
        await fetch_and_save_daily_candles(kiwoom_rest_client, current_date, symbols)

    logger.info("Daily candles collection completed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Collect daily stock candles from Kiwoom API for KRX stocks."
    )
    parser.add_argument(
        "start_date", type=str, help="Start date in ISO 8601 format (YYYY-MM-DD)"
    )
    parser.add_argument(
        "end_date", type=str, help="End date in ISO 8601 format (YYYY-MM-DD)"
    )
    args = parser.parse_args()

    container = Container()
    container.init_resources()
    container.wire(modules=[__name__])

    asyncio.run(main(args.start_date, args.end_date))