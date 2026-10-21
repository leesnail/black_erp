# -*- coding: utf-8 -*-
"""客服：售后 / 发票 / 提醒"""
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AftersaleRecord(Base):
    __tablename__ = "aftersale_record"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_no: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    customer_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    customer_contact: Mapped[str | None] = mapped_column(String(64), nullable=True)
    problem_type: Mapped[str] = mapped_column(String(32))  # 退货/质量问题/物流问题/其他
    description: Mapped[str] = mapped_column(Text)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending|resolved|closed
    handler_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class Invoice(Base):
    __tablename__ = "invoice"

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_no: Mapped[str] = mapped_column(String(64), index=True)
    invoice_type: Mapped[str] = mapped_column(String(16), default="普票")  # 专票|普票
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("supplier.id"), nullable=True)
    invoice_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending|uploaded
    attachment_keys: Mapped[list] = mapped_column(JSON, default=list)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("user.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)


class Reminder(Base):
    __tablename__ = "reminder"

    id: Mapped[int] = mapped_column(primary_key=True)
    rtype: Mapped[str] = mapped_column(String(32), default="invoice")  # invoice|report|batch_timeout
    ref_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    # pending|delivered|read|failed
    retry_count: Mapped[int] = mapped_column(default=0)
    plan_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
