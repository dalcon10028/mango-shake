from datetime import datetime
from decimal import Decimal
from sqlalchemy import Integer, String, DATETIME, Numeric, TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from shared.db import Base


class BitgetSpotOrder(Base):
    __tablename__ = "order_spot_bitget"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String, nullable=False)
    order_id: Mapped[str] = mapped_column("order_id", String, nullable=False, unique=True)
    client_oid: Mapped[str] = mapped_column("client_oid", String, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric, nullable=True)
    size: Mapped[Decimal] = mapped_column("size", Numeric, nullable=False)
    order_type: Mapped[str] = mapped_column("order_type", String, nullable=False)
    side: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    price_avg: Mapped[Decimal] = mapped_column("price_avg", Numeric, nullable=False)
    base_volume: Mapped[Decimal] = mapped_column("base_volume", Numeric, nullable=False)
    quote_volume: Mapped[Decimal] = mapped_column("quote_volume", Numeric, nullable=False)
    enter_point_source: Mapped[str] = mapped_column("enter_point_source", String, nullable=False)
    order_source: Mapped[str] = mapped_column("order_source", String, nullable=True)
    ctime: Mapped[datetime] = mapped_column("c_time", DATETIME, nullable=False)
    utime: Mapped[datetime] = mapped_column("u_time", DATETIME, nullable=False)
    total_fee: Mapped[Decimal] = mapped_column(Numeric, nullable=True)  # feeDetail -> newFees -> t
    fee_detail: Mapped[dict] = mapped_column("fee_detail", JSONB, nullable=True)
    created_at: Mapped["datetime"] = mapped_column(TIMESTAMP(timezone=False), nullable=False, server_default="CURRENT_TIMESTAMP")