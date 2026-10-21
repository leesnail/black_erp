# -*- coding: utf-8 -*-
"""核算：Batch / OrderLine / MatchRule"""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Batch(Base):
    """计算批次（不可变，重算生成新 version）"""

    __tablename__ = "calc_batch"

    id: Mapped[int] = mapped_column(primary_key=True)
    shop_id: Mapped[int] = mapped_column(ForeignKey("shop.id"), index=True)
    period: Mapped[str] = mapped_column(String(7), index=True)  # YYYY-MM
    source_filename: Mapped[str] = mapped_column(String(255))
    source_key: Mapped[str] = mapped_column(String(255))  # Storage key
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    # pending|running|success|failed|settled
    version: Mapped[int] = mapped_column(Integer, default=1)
    stats: Mapped[dict] = mapped_column(JSON, default=dict)
    err_msg: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("user.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class OrderLine(Base):
    __tablename__ = "order_line"

    id: Mapped[int] = mapped_column(primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("calc_batch.id"), index=True)
    order_no: Mapped[str] = mapped_column(String(64), index=True)
    raw_product: Mapped[str] = mapped_column(Text)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    spec_text: Mapped[str | None] = mapped_column(String(128), nullable=True)
    qty: Mapped[int] = mapped_column(Integer, default=1)
    province: Mapped[str | None] = mapped_column(String(32), nullable=True)
    spec_id: Mapped[int | None] = mapped_column(ForeignKey("spec.id"), nullable=True, index=True)
    price_snapshot: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    surcharge: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    unit_cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    line_cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    income: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    matched: Mapped[str] = mapped_column(String(8), default="none", index=True)  # auto|manual|none
    aftersale_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ignored: Mapped[bool] = mapped_column(default=False)
    ignore_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class MatchRule(Base):
    """人工指定沉淀：同文本下次自动命中（优先级 0）"""

    __tablename__ = "match_rule"

    id: Mapped[int] = mapped_column(primary_key=True)
    shop_id: Mapped[int] = mapped_column(ForeignKey("shop.id"), index=True)
    title_norm: Mapped[str] = mapped_column(String(255), index=True)
    spec_text: Mapped[str] = mapped_column(String(128), default="")
    spec_id: Mapped[int] = mapped_column(ForeignKey("spec.id"))
    created_by: Mapped[int | None] = mapped_column(ForeignKey("user.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
