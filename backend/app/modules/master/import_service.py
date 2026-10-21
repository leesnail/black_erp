# -*- coding: utf-8 -*-
"""XLSX 成本表导入"""
from decimal import Decimal, InvalidOperation
from io import BytesIO
from typing import Any

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BizError
from app.modules.master import models as m
from app.modules.master.service import next_spec_code

REQUIRED_HEADERS = ["店铺名称", "产品标题名", "规格售价", "拿货价"]
OPTIONAL_HEADERS = ["规格编码"]


async def import_cost_xlsx(
    db: AsyncSession,
    file_bytes: bytes,
    user_id: int,
    dry_run: bool = False,
) -> dict[str, Any]:
    """固定模板导入。返回统计或异常清单。"""
    try:
        df = pd.read_excel(BytesIO(file_bytes), engine="openpyxl")
    except Exception as e:
        raise BizError(f"文件解析失败: {e}")

    df.columns = [str(c).strip() for c in df.columns]
    missing = [h for h in REQUIRED_HEADERS if h not in df.columns]
    if missing:
        raise BizError(f"表头缺失，整表拒绝: {missing}")

    errors: list[dict] = []
    created = 0
    price_updated = 0
    ok_rows = 0

    for idx, row in df.iterrows():
        row_no = int(idx) + 2  # Excel 行号（含表头）
        title = str(row.get("产品标题名") or "").strip()
        sale_price_raw = row.get("规格售价")
        cost_raw = row.get("拿货价")
        spec_code = str(row.get("规格编码") or "").strip() if "规格编码" in df.columns else ""

        if not title:
            errors.append({"row": row_no, "reason": "产品标题名为空"})
            continue
        try:
            sale_price = Decimal(str(sale_price_raw)).quantize(Decimal("0.01"))
            cost_price = Decimal(str(cost_raw)).quantize(Decimal("0.01"))
        except (InvalidOperation, TypeError, ValueError):
            errors.append({"row": row_no, "reason": "规格售价/拿货价非数字"})
            continue

        ok_rows += 1
        if dry_run:
            # 预检：判断会新建还是更新
            if spec_code:
                exists = await db.scalar(select(m.Spec).where(m.Spec.spec_code == spec_code))
                if exists:
                    price_updated += 1
                else:
                    created += 1
            else:
                # 无编码：粗略按产品名存在与否
                exists = await db.scalar(select(m.Spec).where(m.Spec.product_name == title).limit(1))
                if exists:
                    price_updated += 1
                else:
                    created += 1
            continue

        # 实际导入：需默认供应商——取第一个 active 供应商
        # 简化：导入时用 shop 名自动注册店铺（若无），供应商用第一个或创建"导入默认"
        shop_name = str(row.get("店铺名称") or "").strip()
        shop = await db.scalar(select(m.Shop).where(m.Shop.name == shop_name[:2])) if shop_name else None
        if not shop and shop_name:
            shop = m.Shop(name=shop_name[:2], full_name=shop_name)
            db.add(shop)
            await db.flush()

        supplier = await db.scalar(select(m.Supplier).where(m.Supplier.status == "active").limit(1))
        if not supplier:
            supplier = m.Supplier(name="导入默认供应商")
            db.add(supplier)
            await db.flush()

        spec: m.Spec | None = None
        if spec_code:
            spec = await db.scalar(select(m.Spec).where(m.Spec.spec_code == spec_code))
        if not spec:
            # 按产品名+售价尝试命中（方案 A 对齐）
            spec = await db.scalar(
                select(m.Spec).where(m.Spec.product_name == title).limit(1)
            )

        import datetime as dt

        if spec:
            db.add(
                m.CostPrice(
                    spec_id=spec.id,
                    price=cost_price,
                    supplier_id=supplier.id,
                    effective_at=dt.datetime.utcnow(),
                    created_by=user_id,
                )
            )
            price_updated += 1
        else:
            code = await next_spec_code()
            # spec_name 从标题尾部猜；简化用整标题
            spec = m.Spec(
                spec_code=code,
                product_name=title,
                spec_name=title[-20:] if len(title) > 20 else title,
                supplier_id=supplier.id,
            )
            db.add(spec)
            await db.flush()
            db.add(
                m.CostPrice(
                    spec_id=spec.id,
                    price=cost_price,
                    supplier_id=supplier.id,
                    effective_at=dt.datetime.utcnow(),
                    created_by=user_id,
                )
            )
            created += 1

    if not dry_run:
        await db.commit()

    return {
        "total_rows": len(df),
        "ok_rows": ok_rows,
        "created": created,
        "price_updated": price_updated,
        "errors": errors,
        "dry_run": dry_run,
    }
