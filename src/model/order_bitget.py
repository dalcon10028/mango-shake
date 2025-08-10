from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import Integer, String, DATETIME, Numeric, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column
from shared.db import Base


class BitgetOrder(Base):
    __tablename__ = "order_bitget"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String, nullable=False)
    size: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    order_id: Mapped[str] = mapped_column("order_id", String, nullable=False, unique=True)
    client_oid: Mapped[str] = mapped_column("client_oid", String, nullable=False)
    base_volume: Mapped[Decimal] = mapped_column("base_volume", Numeric, nullable=False)
    fee: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric, nullable=True)
    price_avg: Mapped[Decimal] = mapped_column("price_avg", Numeric, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    side: Mapped[str] = mapped_column(String, nullable=False)
    force: Mapped[str] = mapped_column(String, nullable=False)
    total_profits: Mapped[Decimal] = mapped_column("total_profits", Numeric, nullable=False)
    pos_side: Mapped[str] = mapped_column("pos_side", String, nullable=False)
    margin_coin: Mapped[str] = mapped_column("margin_coin", String, nullable=False)
    quote_volume: Mapped[Decimal] = mapped_column("quote_volume", Numeric, nullable=False)
    leverage: Mapped[int] = mapped_column(Integer, nullable=False)
    margin_mode: Mapped[str] = mapped_column("margin_mode", String, nullable=False)
    enter_point_source: Mapped[str] = mapped_column("enter_point_source", String, nullable=False)
    trade_side: Mapped[str] = mapped_column("trade_side", String, nullable=False)
    pos_mode: Mapped[str] = mapped_column("pos_mode", String, nullable=False)
    order_type: Mapped[str] = mapped_column("order_type", String, nullable=False)
    order_source: Mapped[str] = mapped_column("order_source", String, nullable=True)
    preset_stop_surplus_price: Mapped[Decimal] = mapped_column("preset_stop_surplus_price", Numeric, nullable=True)
    preset_stop_loss_price: Mapped[Decimal] = mapped_column("preset_stop_loss_price", Numeric, nullable=True)
    pos_avg: Mapped[Decimal] = mapped_column("pos_avg", Numeric, nullable=True)
    reduce_only: Mapped[str] = mapped_column("reduce_only", String, nullable=False)
    ctime: Mapped[datetime] = mapped_column("c_time", DATETIME, nullable=False)
    utime: Mapped[datetime] = mapped_column("u_time", DATETIME, nullable=False)
    created_at: Mapped["datetime"] = mapped_column(TIMESTAMP(timezone=False), nullable=False, server_default="CURRENT_TIMESTAMP")