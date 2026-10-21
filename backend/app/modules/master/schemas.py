# -*- coding: utf-8 -*-
"""master 输入输出 schema"""
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class SupplierCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    wechat_group: str | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    products: str | None = None
    remark: str | None = None


class SupplierUpdate(BaseModel):
    name: str | None = None
    wechat_group: str | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    products: str | None = None
    remark: str | None = None


class SupplierOut(BaseModel):
    id: int
    name: str
    wechat_group: str | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    products: str | None = None
    remark: str | None = None
    status: str

    model_config = {"from_attributes": True}


class SpecCreate(BaseModel):
    product_name: str = Field(min_length=1, max_length=255)
    spec_name: str = Field(min_length=1, max_length=128)
    supplier_id: int
    price: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    image_key: str | None = None
    remark: str | None = None


class SpecOut(BaseModel):
    id: int
    spec_code: str
    product_name: str
    spec_name: str
    supplier_id: int
    status: str
    price: Decimal | None = None
    updated_at: datetime | None = None


class SpecPickerItem(BaseModel):
    spec_id: int
    spec_code: str
    product_name: str
    spec_name: str
    price: Decimal | None = None


class CostPriceOut(BaseModel):
    id: int
    spec_id: int
    price: Decimal
    effective_at: datetime
    created_by: int | None = None

    model_config = {"from_attributes": True}


class ShopProductCreate(BaseModel):
    shop_id: int
    title_keyword: str = Field(min_length=1, max_length=255)
    link_id: str | None = None
    spec_id: int
    sale_price: Decimal = Field(ge=0, max_digits=10, decimal_places=2)


class ShopProductOut(BaseModel):
    id: int
    shop_id: int
    shop_name: str = ""
    title_keyword: str
    link_id: str | None = None
    spec_id: int
    spec_code: str = ""
    spec_name: str = ""
    sale_price: Decimal
    status: str


class RoiCreate(BaseModel):
    shop_id: int
    period: str = Field(pattern=r"^\d{4}-\d{2}$")
    spend: Decimal = Field(ge=0)
    deal_amount: Decimal = Field(ge=0)


class RoiOut(BaseModel):
    id: int
    shop_id: int
    period: str
    spend: Decimal
    deal_amount: Decimal
    roi: Decimal | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
