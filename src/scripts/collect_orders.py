import asyncio
import logging
from datetime import datetime

from decimal import Decimal
from sqlalchemy.dialects.postgresql import insert
from model.order_bitget import BitgetOrder
from shared.db import get_db
from dependency_injector.wiring import inject, Provide
from shared.containers import Container

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


@inject
async def main(
    bitget_future_trade_client: Container.bitget_future_trade_client = Provide[Container.bitget_future_trade_client],
):
    logger.info("Starting order collection...")
    async with bitget_future_trade_client as client:
        orders = await client.get_history_orders(
            product_type="USDT-FUTURES",
        )
        logger.info(f"Fetched {len(orders)} orders.")

    # db 저장
    # db 저장
    order_dicts = orders.get("data", {}).get("entrustedList", [])
    if order_dicts:
        # prepare records for upsert
        records = []
        for o in order_dicts:
            records.append({
                "symbol": o.get("symbol"),
                "size": Decimal(o.get("size") or 0),
                "order_id": o.get("orderId"),
                "client_oid": o.get("clientOid"),
                "base_volume": Decimal(o.get("baseVolume") or 0),
                "fee": Decimal(o.get("fee") or 0),
                "price": Decimal(o.get("price") or 0) if o.get("price") else None,
                "price_avg": Decimal(o.get("priceAvg") or 0),
                "status": o.get("status"),
                "side": o.get("side"),
                "force": o.get("force"),
                "total_profits": Decimal(o.get("totalProfits") or 0),
                "pos_side": o.get("posSide"),
                "margin_coin": o.get("marginCoin"),
                "quote_volume": Decimal(o.get("quoteVolume") or 0),
                "leverage": int(o.get("leverage") or 0),
                "margin_mode": o.get("marginMode"),
                "enter_point_source": o.get("enterPointSource"),
                "trade_side": o.get("tradeSide"),
                "pos_mode": o.get("posMode"),
                "order_type": o.get("orderType"),
                "order_source": o.get("orderSource"),
                "preset_stop_surplus_price": Decimal(o.get("presetStopSurplusPrice") or 0) if o.get("presetStopSurplusPrice") else None,
                "preset_stop_loss_price": Decimal(o.get("presetStopLossPrice") or 0) if o.get("presetStopLossPrice") else None,
                "pos_avg": Decimal(o.get("posAvg") or 0) if o.get("posAvg") else None,
                "reduce_only": o.get("reduceOnly"),
                "c_time": datetime.fromtimestamp(int(o.get("cTime")) / 1000) if o.get("cTime") else None,
                "u_time": datetime.fromtimestamp(int(o.get("uTime")) / 1000) if o.get("uTime") else None,
            })

        # perform upsert
        async with get_db() as session:
            stmt = insert(BitgetOrder).values(records)
            stmt = stmt.on_conflict_do_update(
                index_elements=["order_id"],
                set_={col: stmt.excluded[col] for col in records[0].keys() if col != "order_id"},
            )
            await session.execute(stmt)
            await session.commit()
        logger.info(f"Upserted {len(records)} orders into database.")
    else:
        logger.info("No orders to upsert.")

    logger.info("Order collection completed successfully.")


if __name__ == "__main__":
    container = Container()
    container.init_resources()
    container.wire(modules=[__name__])

    asyncio.run(main())