from datetime import datetime
from typing import Literal
from sqlalchemy import Integer, String, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column
from shared.db import Base

class TickerSymbol(Base):
    __tablename__ = "ticker_symbol"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(30), nullable=False)
    base_currency: Mapped[str] = mapped_column(String(10), nullable=False)
    name: Mapped[str] = mapped_column(String(30), nullable=False)
    market: Mapped[Literal["CRYPTO_CURRENCY"]] = mapped_column(String(30), nullable=False)
    created_at: Mapped["datetime"] = mapped_column(TIMESTAMP(timezone=False), nullable=False, server_default="CURRENT_TIMESTAMP")