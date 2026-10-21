# -*- coding: utf-8 -*-
"""calc schema"""
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class PreviewOut(BaseModel):
    total: int = 0
    no_ship_skip: int = 0
    aftersale: int = 0
    qty_invalid: int = 0
    est_unmatched: int = 0
    shop_name: str = ""
    errors: list[dict] = []


class BatchOut(BaseModel):
    id: int
    shop_id: int
    shop_name: str = ""
    period: str
    source_filename: str
    status: str
    version: int
    stats: dict = {}
    err_msg: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class LineOut(BaseModel):
    id: int
    order_no: str
    raw_product: str
    title: str | None = None
    spec_text: str | None = None
    qty: int
    province: str | None = None
    spec_id: int | None = None
    spec_code: str | None = None
    price_snapshot: Decimal | None = None
    surcharge: Decimal
    unit_cost: Decimal | None = None
    line_cost: Decimal | None = None
    income: Decimal
    matched: str
    aftersale_status: str | None = None
    ignored: bool = False

    model_config = {"from_attributes": True}


class UnmatchedLineOut(LineOut):
    recommend: list[dict] = []


class ManualMatchIn(BaseModel):
    line_ids: list[int]
    spec_id: int


class IgnoreIn(BaseModel):
    line_ids: list[int]
    reason: str
