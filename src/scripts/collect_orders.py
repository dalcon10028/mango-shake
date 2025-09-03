import asyncio
import json
import logging
from datetime import datetime

from decimal import Decimal
from sqlalchemy.dialects.postgresql import insert

from exchange.bitget import BitgetFutureTradeClient
from exchange.bitget.spot.spot_trade_client import BitgetSpotTradeClient
from model.order_bitget import BitgetOrder
from model.order_spot_bitget import BitgetSpotOrder
from shared.db import get_db
from dependency_injector.wiring import inject, Provide
from shared.containers import Container

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

async def collect_bitget_spot_orders(client: BitgetSpotTradeClient):
    logger.info("Starting collection of Bitget spot orders...")
    async with client:
        orders = await client.get_history_orders(
            symbol="",
        )

    # db 저장
    order_dicts = orders.get("data", [])
    logger.info(f"Fetched {len(order_dicts)} orders.")
    if order_dicts:
        records = []

        def d(val):
            return Decimal(val) if val not in (None, "") else None

        def d0(val):
            try:
                return Decimal(val) if val not in (None, "") else Decimal(0)
            except Exception:
                return Decimal(0)

        for o in order_dicts:
            raw_fee_detail = o.get("feeDetail") or o.get("fee_detail") or {}
            if isinstance(raw_fee_detail, str):
                try:
                    fee_detail = json.loads(raw_fee_detail)
                except Exception:
                    fee_detail = {}
            elif isinstance(raw_fee_detail, dict):
                fee_detail = raw_fee_detail
            else:
                fee_detail = {}

            # Compute total_fee from fee_detail if available
            total_fee = fee_detail.get("newFees").get("t") if fee_detail.get("newFees") else None

            # Build record
            records.append({
                "symbol": o.get("symbol"),
                "order_id": o.get("orderId") or o.get("order_id"),
                "client_oid": o.get("clientOid") or o.get("client_oid"),
                "price": d(o.get("price")),
                "size": d0(o.get("size")),
                "order_type": o.get("orderType") or o.get("order_type"),
                "side": o.get("side"),
                "status": o.get("status"),
                "price_avg": d0(o.get("priceAvg") or o.get("price_avg")),
                "base_volume": d0(o.get("baseVolume") or o.get("base_volume")),
                "quote_volume": d0(o.get("quoteVolume") or o.get("quote_volume")),
                "enter_point_source": o.get("enterPointSource") or o.get("enter_point_source"),
                "order_source": o.get("orderSource") or o.get("order_source"),
                "c_time": (
                    datetime.fromtimestamp(int(o.get("cTime")) / 1000) if o.get("cTime")
                    else (datetime.fromtimestamp(int(o.get("ctime")) / 1000) if o.get("ctime") else None)
                ),
                "u_time": (
                    datetime.fromtimestamp(int(o.get("uTime")) / 1000) if o.get("uTime")
                    else (datetime.fromtimestamp(int(o.get("utime")) / 1000) if o.get("utime") else None)
                ),
                "total_fee": total_fee,
                "fee_detail": fee_detail,
            })

        # Upsert into DB
        async with get_db() as session:
            stmt = insert(BitgetSpotOrder).values(records)
            stmt = stmt.on_conflict_do_update(
                index_elements=["order_id"],
                set_={col: stmt.excluded[col] for col in records[0].keys() if col != "order_id"},
            )
            await session.execute(stmt)
            await session.commit()
        logger.info(f"Upserted {len(records)} spot orders into database.")
    else:
        logger.info("No spot orders to upsert.")




async def collect_bitget_future_orders(client: BitgetFutureTradeClient):
    logger.info("Starting collection of Bitget future orders...")
    async with client:
        orders = await client.get_history_orders(
            product_type="USDT-FUTURES",
        )
        logger.info(f"Fetched {len(orders)} orders.")

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
        logger.info(f"Upserted {len(records)} future orders into database.")
    else:
        logger.info("No future orders to upsert.")


@inject
async def main(
    bitget_future_trade_client: BitgetFutureTradeClient = Provide[Container.bitget_future_trade_client],
    bitget_spot_trade_client: BitgetSpotTradeClient = Provide[Container.bitget_spot_trade_client],
):
    await collect_bitget_future_orders(bitget_future_trade_client)
    await collect_bitget_spot_orders(bitget_spot_trade_client)


    logger.info("Order collection completed successfully.")


if __name__ == "__main__":
    container = Container()
    container.init_resources()
    container.wire(modules=[__name__])

    asyncio.run(main())