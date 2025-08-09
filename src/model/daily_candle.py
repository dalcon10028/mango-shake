from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import Integer, String, DATETIME, Numeric, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column
from shared.db import Base


class DailyCandle(Base):
    __tablename__ = "daily_candle"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    exchange: Mapped[str] = mapped_column(String(10), nullable=False)
    base_date: Mapped["date"] = mapped_column(DATETIME(timezone=False), nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String(30), nullable=False)
    open: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    volume: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    created_at: Mapped["datetime"] = mapped_column(TIMESTAMP(timezone=False), nullable=False, server_default="CURRENT_TIMESTAMP")