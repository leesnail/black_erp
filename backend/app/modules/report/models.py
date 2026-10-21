# -*- coding: utf-8 -*-
"""报表：日报"""
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class DailyReport(Base):
    __tablename__ = "daily_report"
    __table_args__ = (UniqueConstraint("shop_id", "report_date", name="uk_shop_day"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    shop_id: Mapped[int] = mapped_column(ForeignKey("shop.id"), index=True)
    report_date: Mapped[date] = mapped_column(Date, index=True)
    order_count: Mapped[int] = mapped_column(Integer, default=0)
    income_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    cost_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    profit: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
