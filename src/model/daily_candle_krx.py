from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import Integer, String, DATE, Numeric, TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from shared.db import Base

class DailyCandleKrx(Base):
    __tablename__ = "daily_candle_krx"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(30), nullable=False)
    date: Mapped[date] = mapped_column(DATE, nullable=False)
    open_price: Mapped[Decimal] = mapped_column(Numeric, nullable=False, comment="시가")
    high_price: Mapped[Decimal] = mapped_column(Numeric, nullable=False, comment="고가")
    low_price: Mapped[Decimal] = mapped_column(Numeric, nullable=False, comment="저가")
    close_price: Mapped[Decimal] = mapped_column(Numeric, nullable=False, comment="종가")
    price_change: Mapped[Decimal] = mapped_column(Numeric, nullable=False, comment="전일비")
    fluctuation_rate: Mapped[Decimal] = mapped_column(Numeric, nullable=False, comment="등락률")
    volume: Mapped[Decimal] = mapped_column(Numeric, nullable=False, comment="거래량")
    trade_amount: Mapped[Decimal] = mapped_column(Numeric, nullable=False, comment="거래대금(백만)")
    credit_ratio: Mapped[Decimal] = mapped_column(Numeric, nullable=False, comment="신용비")
    individual_trade_volume: Mapped[Decimal] = mapped_column(Numeric, nullable=False, comment="개인 거래량")
    institution_trade_volume: Mapped[Decimal] = mapped_column(Numeric, nullable=False, comment="기관 거래량")
    foreign_trade_volume: Mapped[Decimal] = mapped_column(Numeric, nullable=False, comment="외인수량")
    foreign_company_trade_volume: Mapped[Decimal] = mapped_column(Numeric, nullable=False, comment="외국계")
    program_trade_volume: Mapped[Decimal] = mapped_column(Numeric, nullable=False, comment="프로그램")
    foreign_ownership_ratio: Mapped[Decimal] = mapped_column(Numeric, nullable=False, comment="외인비")
    foreign_shares_held: Mapped[Decimal] = mapped_column(Numeric, nullable=False, comment="외인보유")
    foreign_ownership_weight: Mapped[Decimal] = mapped_column(Numeric, nullable=False, comment="외인비중")
    foreign_net_purchase: Mapped[Decimal] = mapped_column(Numeric, nullable=False, comment="외인순매수")
    institution_net_purchase: Mapped[Decimal] = mapped_column(Numeric, nullable=False, comment="기관순매수")
    individual_net_purchase: Mapped[Decimal] = mapped_column(Numeric, nullable=False, comment="개인순매수")
    credit_balance_ratio: Mapped[Decimal] = mapped_column(Numeric, nullable=False, comment="신용잔고율")
    response: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=False), nullable=False, server_default="CURRENT_TIMESTAMP"
    )

    __table_args__ = (
        {"comment": "국내주식 일별 캔들"},
        {"schema": "public"},
    )
