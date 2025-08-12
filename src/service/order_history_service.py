from sqlalchemy import select
from model.order_bitget import BitgetOrder
from shared.db import get_db


async def get_order_histories() -> list[BitgetOrder]:
    """
    Fetches all order histories from the database.

    Returns:
        list[BitgetOrder]: A list of BitgetOrder objects.
    """
    async with get_db() as session:
        stmt = select(BitgetOrder)
        result = await session.execute(stmt)
        return result.scalars().all()