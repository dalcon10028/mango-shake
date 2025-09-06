from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import Integer, String, DATETIME, Numeric, TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from shared.db import Base

class ConditionSearchResult(Base):
    __tablename__ = "condition_search_result"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    base_date: Mapped["date"] = mapped_column(DATETIME(timezone=False), nullable=False, index=True)
    condition_id: Mapped[str] = mapped_column(String(30), nullable=False) # 조건식 번호
    symbol: Mapped[str] = mapped_column(String(30), nullable=False) # 종목코드
    name: Mapped[str] = mapped_column(String(100), nullable=False) # 종목명
    price: Mapped[Decimal] = mapped_column(Numeric, nullable=False) # 현재가
    change_sign: Mapped[str] = mapped_column(String(5), nullable=False) # 전일대비기호
    change_price: Mapped[Decimal] = mapped_column(Numeric, nullable=False) # 전일대비
    change_rate: Mapped[Decimal] = mapped_column(Numeric, nullable=False) # 등락율
    volume_acc: Mapped[Decimal] = mapped_column(Numeric, nullable=False) # 누적거래량
    open: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    response: Mapped[dict] = mapped_column(JSONB, nullable=False) # 원본 응답 데이터 전체
    created_at: Mapped["datetime"] = mapped_column(TIMESTAMP(timezone=False), nullable=False, server_default="CURRENT_TIMESTAMP")