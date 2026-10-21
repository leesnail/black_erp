# -*- coding: utf-8 -*-
"""主数据路由：供应商 / 规格成本 / 登记 / 地区规则 / ROI"""
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.schemas import Ok, Page
from app.core.database import get_db
from app.core.exceptions import BizError, ConflictError, NotFoundError
from app.core.redis import redis
from app.core.security import SessionUser, current_user, perm
from app.core.audit import audit_log
from app.modules.master import models as m
from app.modules.master.service import next_spec_code
from app.modules.master.schemas import (
    CostPriceOut,
    RoiCreate,
    RoiOut,
    ShopProductCreate,
    ShopProductOut,
    SpecCreate,
    SpecOut,
    SpecPickerItem,
    SupplierCreate,
    SupplierOut,
    SupplierUpdate,
)

router = APIRouter(prefix="/master", tags=["master"])


# ---------- 供应商 ----------


@router.get("/suppliers", response_model=list[SupplierOut])
async def list_suppliers(
    q: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: SessionUser = Depends(perm("master.supplier.list")),
):
    stmt = select(m.Supplier).where(m.Supplier.status == "active")
    if q:
        stmt = stmt.where(or_(m.Supplier.name.contains(q), m.Supplier.contact_name.contains(q)))
    rows = (await db.scalars(stmt.order_by(m.Supplier.id.desc()))).all()
    return rows


@router.post("/suppliers", response_model=SupplierOut)
async def create_supplier(
    body: SupplierCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: SessionUser = Depends(perm("master.supplier.create")),
):
    obj = m.Supplier(**body.model_dump())
    db.add(obj)
    await db.flush()
    await audit_log(db, user.uid, "master.supplier", "create", str(obj.id), after=body.model_dump())
    await db.commit()
    await db.refresh(obj)
    return obj


@router.patch("/suppliers/{sid}", response_model=SupplierOut)
async def update_supplier(
    sid: int,
    body: SupplierUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: SessionUser = Depends(perm("master.supplier.update")),
):
    obj = await db.get(m.Supplier, sid)
    if not obj:
        raise NotFoundError("供应商不存在")
    before = {"name": obj.name, "wechat_group": obj.wechat_group}
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    await audit_log(db, user.uid, "master.supplier", "update", str(sid), before=before, after=body.model_dump())
    await db.commit()
    await db.refresh(obj)
    return obj


# ---------- 规格成本表 ----------


@router.get("/specs", response_model=Page[SpecOut])
async def list_specs(
    q: str | None = None,
    supplier_id: int | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: SessionUser = Depends(perm("master.spec.list")),
):
    stmt = select(m.Spec)
    count_stmt = select(func.count()).select_from(m.Spec)
    if q:
        cond = or_(
            m.Spec.spec_code.contains(q),
            m.Spec.product_name.contains(q),
            m.Spec.spec_name.contains(q),
        )
        stmt = stmt.where(cond)
        count_stmt = count_stmt.where(cond)
    if supplier_id:
        stmt = stmt.where(m.Spec.supplier_id == supplier_id)
        count_stmt = count_stmt.where(m.Spec.supplier_id == supplier_id)
    if status:
        stmt = stmt.where(m.Spec.status == status)
        count_stmt = count_stmt.where(m.Spec.status == status)

    total = (await db.scalar(count_stmt)) or 0
    rows = (
        await db.scalars(
            stmt.order_by(m.Spec.id.desc()).offset((page - 1) * page_size).limit(page_size)
        )
    ).all()

    # 批量取当前价（每 spec 最新一条）
    ids = [r.id for r in rows]
    price_map: dict[int, Decimal] = {}
    if ids:
        sub = (
            select(m.CostPrice.spec_id, func.max(m.CostPrice.effective_at).label("mx"))
            .where(m.CostPrice.spec_id.in_(ids))
            .group_by(m.CostPrice.spec_id)
            .subquery()
        )
        price_rows = await db.execute(
            select(m.CostPrice.spec_id, m.CostPrice.price)
            .join(sub, (m.CostPrice.spec_id == sub.c.spec_id) & (m.CostPrice.effective_at == sub.c.mx))
        )
        price_map = dict(price_rows.all())

    items = [
        SpecOut(
            id=r.id,
            spec_code=r.spec_code,
            product_name=r.product_name,
            spec_name=r.spec_name,
            supplier_id=r.supplier_id,
            status=r.status,
            price=price_map.get(r.id),
            updated_at=r.updated_at,
        )
        for r in rows
    ]
    return Page(items=items, total=total, page=page, page_size=page_size)


@router.get("/spec-picker", response_model=list[SpecPickerItem])
async def spec_picker(
    q: str | None = None,
    shop_id: int | None = None,
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    user: SessionUser = Depends(current_user),
):
    """选择器：任意已登录角色可用（登记/未匹配指定复用）"""
    stmt = select(m.Spec).where(m.Spec.status == "active")
    if q:
        stmt = stmt.where(
            or_(
                m.Spec.spec_code.contains(q),
                m.Spec.product_name.contains(q),
                m.Spec.spec_name.contains(q),
            )
        )
    rows = (await db.scalars(stmt.order_by(m.Spec.spec_code).limit(limit))).all()
    ids = [r.id for r in rows]
    price_map: dict[int, Decimal] = {}
    if ids:
        sub = (
            select(m.CostPrice.spec_id, func.max(m.CostPrice.effective_at).label("mx"))
            .where(m.CostPrice.spec_id.in_(ids))
            .group_by(m.CostPrice.spec_id)
            .subquery()
        )
        price_rows = await db.execute(
            select(m.CostPrice.spec_id, m.CostPrice.price)
            .join(sub, (m.CostPrice.spec_id == sub.c.spec_id) & (m.CostPrice.effective_at == sub.c.mx))
        )
        price_map = dict(price_rows.all())
    return [
        SpecPickerItem(
            spec_id=r.id,
            spec_code=r.spec_code,
            product_name=r.product_name,
            spec_name=r.spec_name,
            price=price_map.get(r.id),
        )
        for r in rows
    ]


@router.post("/specs", response_model=SpecOut)
async def create_spec(
    body: SpecCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: SessionUser = Depends(perm("master.spec.create")),
):
    supplier = await db.get(m.Supplier, body.supplier_id)
    if not supplier or supplier.status != "active":
        raise BizError("供应商无效")

    code = await next_spec_code()
    spec = m.Spec(
        spec_code=code,
        product_name=body.product_name,
        spec_name=body.spec_name,
        supplier_id=body.supplier_id,
        image_key=body.image_key,
        remark=body.remark,
    )
    db.add(spec)
    await db.flush()
    db.add(
        m.CostPrice(
            spec_id=spec.id,
            price=body.price,
            supplier_id=body.supplier_id,
            effective_at=datetime.now(timezone.utc).replace(tzinfo=None),
            created_by=user.uid,
        )
    )
    await audit_log(db, user.uid, "master.spec", "create", code, after={"code": code, "price": str(body.price)})
    await db.commit()
    await db.refresh(spec)
    return SpecOut(
        id=spec.id,
        spec_code=spec.spec_code,
        product_name=spec.product_name,
        spec_name=spec.spec_name,
        supplier_id=spec.supplier_id,
        status=spec.status,
        price=body.price,
        updated_at=spec.updated_at,
    )


@router.patch("/specs/{sid}", response_model=SpecOut)
async def update_spec(
    sid: int,
    body: SpecCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: SessionUser = Depends(perm("master.spec.update")),
):
    spec = await db.get(m.Spec, sid)
    if not spec:
        raise NotFoundError("规格不存在")
    spec.product_name = body.product_name
    spec.spec_name = body.spec_name
    spec.supplier_id = body.supplier_id
    if body.image_key:
        spec.image_key = body.image_key
    if body.remark is not None:
        spec.remark = body.remark
    # 改价 = 追加历史
    db.add(
        m.CostPrice(
            spec_id=spec.id,
            price=body.price,
            supplier_id=body.supplier_id,
            effective_at=datetime.now(timezone.utc).replace(tzinfo=None),
            created_by=user.uid,
        )
    )
    await audit_log(db, user.uid, "master.spec", "update", spec.spec_code)
    await db.commit()
    await db.refresh(spec)
    return SpecOut(
        id=spec.id,
        spec_code=spec.spec_code,
        product_name=spec.product_name,
        spec_name=spec.spec_name,
        supplier_id=spec.supplier_id,
        status=spec.status,
        price=body.price,
        updated_at=spec.updated_at,
    )


@router.post("/specs/import-xlsx")
async def import_specs_xlsx(
    file: UploadFile = File(...),
    dry_run: bool = Form(default=True),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
    user: SessionUser = Depends(perm("master.spec.import")),
):
    """固定模板 XLSX 导入：dry_run=1 预检，0 正式导入"""
    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xlsm")):
        raise BizError("仅支持 .xlsx 文件")
    from app.modules.master.import_service import import_cost_xlsx

    content = await file.read()
    result = await import_cost_xlsx(db, content, user.uid, dry_run=dry_run)
    await audit_log(
        db, user.uid, "master.spec", "import_xlsx", file.filename,
        after={"dry_run": dry_run, "created": result["created"], "updated": result["price_updated"]},
    )
    if not dry_run:
        await db.commit()
    return result


@router.post("/specs/{sid}/price", response_model=Ok)
async def update_price(
    sid: int,
    price: Decimal,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: SessionUser = Depends(perm("master.spec.price_write")),
):
    spec = await db.get(m.Spec, sid)
    if not spec:
        raise NotFoundError("规格不存在")
    old = await db.scalar(
        select(m.CostPrice.price)
        .where(m.CostPrice.spec_id == sid)
        .order_by(m.CostPrice.effective_at.desc())
        .limit(1)
    )
    db.add(
        m.CostPrice(
            spec_id=sid,
            price=price,
            supplier_id=spec.supplier_id,
            effective_at=datetime.now(timezone.utc).replace(tzinfo=None),
            created_by=user.uid,
        )
    )
    await audit_log(db, user.uid, "master.spec", "price", spec.spec_code, before={"price": str(old)}, after={"price": str(price)})
    await db.commit()
    return Ok(detail=f"价格已更新为 {price}")


@router.get("/specs/{sid}/price-history", response_model=list[CostPriceOut])
async def price_history(
    sid: int,
    db: AsyncSession = Depends(get_db),
    user: SessionUser = Depends(perm("master.spec.list")),
):
    rows = (
        await db.scalars(
            select(m.CostPrice).where(m.CostPrice.spec_id == sid).order_by(m.CostPrice.effective_at.desc())
        )
    ).all()
    return rows


@router.post("/specs/{sid}/disable", response_model=Ok)
async def disable_spec(
    sid: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: SessionUser = Depends(perm("master.spec.update")),
):
    spec = await db.get(m.Spec, sid)
    if not spec:
        raise NotFoundError("规格不存在")
    spec.status = "disabled"
    await audit_log(db, user.uid, "master.spec", "disable", spec.spec_code)
    await db.commit()
    return Ok(detail="已停用")


# ---------- 店铺产品登记 ----------


@router.get("/shop-products", response_model=Page[ShopProductOut])
async def list_shop_products(
    shop_id: int | None = None,
    q: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: SessionUser = Depends(perm("master.shop_product.list")),
):
    stmt = select(m.ShopProduct)
    count_stmt = select(func.count()).select_from(m.ShopProduct)
    if shop_id:
        stmt = stmt.where(m.ShopProduct.shop_id == shop_id)
        count_stmt = count_stmt.where(m.ShopProduct.shop_id == shop_id)
    if q:
        cond = m.ShopProduct.title_keyword.contains(q)
        stmt = stmt.where(cond)
        count_stmt = count_stmt.where(cond)
    total = (await db.scalar(count_stmt)) or 0
    rows = (
        await db.scalars(
            stmt.order_by(m.ShopProduct.id.desc()).offset((page - 1) * page_size).limit(page_size)
        )
    ).all()

    # join spec + shop 展示
    items: list[ShopProductOut] = []
    for r in rows:
        spec = await db.get(m.Spec, r.spec_id)
        shop = await db.get(m.Shop, r.shop_id)
        items.append(
            ShopProductOut(
                id=r.id,
                shop_id=r.shop_id,
                shop_name=shop.name if shop else "",
                title_keyword=r.title_keyword,
                link_id=r.link_id,
                spec_id=r.spec_id,
                spec_code=spec.spec_code if spec else "",
                spec_name=spec.spec_name if spec else "",
                sale_price=r.sale_price,
                status=r.status,
            )
        )
    return Page(items=items, total=total, page=page, page_size=page_size)


@router.post("/shop-products", response_model=ShopProductOut)
async def create_shop_product(
    body: ShopProductCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: SessionUser = Depends(perm("master.shop_product.create")),
):
    shop = await db.get(m.Shop, body.shop_id)
    if not shop:
        raise BizError("店铺不存在")
    spec = await db.get(m.Spec, body.spec_id)
    if not spec or spec.status != "active":
        raise BizError("规格无效或已停用，请从选择器重新选择")

    exists = await db.scalar(
        select(m.ShopProduct).where(
            m.ShopProduct.shop_id == body.shop_id,
            m.ShopProduct.title_keyword == body.title_keyword,
            m.ShopProduct.sale_price == body.sale_price,
        )
    )
    if exists:
        raise ConflictError("同店铺下该标题+售价已登记")

    obj = m.ShopProduct(
        shop_id=body.shop_id,
        title_keyword=body.title_keyword,
        link_id=body.link_id,
        spec_id=body.spec_id,
        sale_price=body.sale_price,
        created_by=user.uid,
    )
    db.add(obj)
    await db.flush()
    await audit_log(db, user.uid, "master.shop_product", "create", str(obj.id))
    await db.commit()
    await db.refresh(obj)
    return ShopProductOut(
        id=obj.id,
        shop_id=obj.shop_id,
        shop_name=shop.name,
        title_keyword=obj.title_keyword,
        link_id=obj.link_id,
        spec_id=obj.spec_id,
        spec_code=spec.spec_code,
        spec_name=spec.spec_name,
        sale_price=obj.sale_price,
        status=obj.status,
    )


@router.patch("/shop-products/{pid}/status", response_model=Ok)
async def toggle_shop_product(
    pid: int,
    status: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: SessionUser = Depends(perm("master.shop_product.update")),
):
    if status not in ("active", "disabled"):
        raise BizError("status 无效")
    obj = await db.get(m.ShopProduct, pid)
    if not obj:
        raise NotFoundError("登记不存在")
    obj.status = status
    await db.commit()
    return Ok(detail="已更新")


# ---------- ROI ----------


@router.get("/roi-records", response_model=list[RoiOut])
async def list_roi(
    shop_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    user: SessionUser = Depends(perm("roi.list")),
):
    stmt = select(m.RoiRecord)
    if shop_id:
        stmt = stmt.where(m.RoiRecord.shop_id == shop_id)
    rows = (await db.scalars(stmt.order_by(m.RoiRecord.id.desc()).limit(100))).all()
    return rows


@router.post("/roi-records", response_model=RoiOut)
async def create_roi(
    body: RoiCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: SessionUser = Depends(perm("roi.create")),
):
    roi = (body.deal_amount / body.spend).quantize(Decimal("0.01")) if body.spend else None
    obj = m.RoiRecord(
        shop_id=body.shop_id,
        period=body.period,
        spend=body.spend,
        deal_amount=body.deal_amount,
        roi=roi,
        created_by=user.uid,
    )
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


# ---------- 店铺列表（选择器用） ----------


@router.get("/shops")
async def list_shops(
    db: AsyncSession = Depends(get_db),
    user: SessionUser = Depends(current_user),
):
    rows = (await db.scalars(select(m.Shop).where(m.Shop.status == "active"))).all()
    return [{"id": r.id, "name": r.name, "full_name": r.full_name} for r in rows]


# ---------- 地区规则 ----------


@router.get("/region-rules")
async def list_region_rules(
    db: AsyncSession = Depends(get_db),
    user: SessionUser = Depends(current_user),
):
    rows = (await db.scalars(select(m.RegionRule).where(m.RegionRule.status == "active"))).all()
    return [
        {"id": r.id, "name": r.name, "provinces": r.provinces, "amount": str(r.amount), "unit": r.unit}
        for r in rows
    ]
