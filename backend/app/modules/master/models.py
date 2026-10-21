# -*- coding: utf-8 -*-
"""主数据：Supplier / Shop / Spec / CostPrice / ShopProduct / RegionRule"""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Shop(Base):
    __tablename__ = "shop"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(32), unique=True)  # 文件名前2字匹配
    full_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="active")


class Supplier(Base):
    __tablename__ = "supplier"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), index=True)
    wechat_group: Mapped[str | None] = mapped_column(String(128), nullable=True)
    contact_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    products: Mapped[str | None] = mapped_column(Text, nullable=True)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Spec(Base):
    """规格（全系统主键载体）"""

    __tablename__ = "spec"

    id: Mapped[int] = mapped_column(primary_key=True)
    spec_code: Mapped[str] = mapped_column(String(16), unique=True, index=True)  # SP+6位
    product_name: Mapped[str] = mapped_column(String(255), index=True)
    spec_name: Mapped[str] = mapped_column(String(128))
    supplier_id: Mapped[int] = mapped_column(ForeignKey("supplier.id"))
    image_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="active")  # active|disabled
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class CostPrice(Base):
    """价格历史（只追加不更新）"""

    __tablename__ = "cost_price"

    id: Mapped[int] = mapped_column(primary_key=True)
    spec_id: Mapped[int] = mapped_column(ForeignKey("spec.id"), index=True)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("supplier.id"), nullable=True)
    effective_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("user.id"), nullable=True)


class ShopProduct(Base):
    """店铺产品登记"""

    __tablename__ = "shop_product"
    __table_args__ = (
        UniqueConstraint("shop_id", "title_keyword", "sale_price", name="uk_shop_title_price"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    shop_id: Mapped[int] = mapped_column(ForeignKey("shop.id"), index=True)
    title_keyword: Mapped[str] = mapped_column(String(255), index=True)
    link_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    spec_id: Mapped[int] = mapped_column(ForeignKey("spec.id"))
    sale_price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    status: Mapped[str] = mapped_column(String(16), default="active")
    created_by: Mapped[int | None] = mapped_column(ForeignKey("user.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class RegionRule(Base):
    """地区附加成本（按件）"""

    __tablename__ = "region_rule"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64))
    provinces: Mapped[list] = mapped_column(JSON)  # ["新疆维吾尔自治区", ...]
    amount: Mapped[Decimal] = mapped_column(Numeric(6, 2))  # +4 / +20
    unit: Mapped[str] = mapped_column(String(16), default="per_piece")
    status: Mapped[str] = mapped_column(String(16), default="active")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class RoiRecord(Base):
    __tablename__ = "roi_record"

    id: Mapped[int] = mapped_column(primary_key=True)
    shop_id: Mapped[int] = mapped_column(ForeignKey("shop.id"))
    period: Mapped[str] = mapped_column(String(7))  # YYYY-MM
    spend: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    deal_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    roi: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("user.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
