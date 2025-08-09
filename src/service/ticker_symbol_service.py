from typing import Literal

from sqlalchemy import select
from model.ticker_symbol import TickerSymbol
from shared.db import get_db


async def get_by_market(ticker_symbol: Literal["CRYPTO_CURRENCY"]) -> list[TickerSymbol]:
    """
    Fetches ticker symbols by market.

    Args:
        ticker_symbol (str): The market to filter by.

    Returns:
        list[TickerSymbol]: A list of TickerSymbol objects matching the market.
    """
    async with get_db() as session:
        stmt = select(TickerSymbol).where(TickerSymbol.market == ticker_symbol)
        result = await session.execute(stmt)
        return result.scalars().all()