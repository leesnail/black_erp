# -*- coding: utf-8 -*-
"""客服模块路由"""
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.schemas import Ok, Page
from app.core.audit import audit_log
from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.core.security import SessionUser, perm
from app.modules.service import models as sm

router = APIRouter(prefix="/service", tags=["service"])


# ---------- 售后 ----------


@router.get("/aftersales", response_model=Page[dict])
async def list_aftersales(
    q: str | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: SessionUser = Depends(perm("service.list")),
):
    stmt = select(sm.AftersaleRecord)
    count_stmt = select(func.count()).select_from(sm.AftersaleRecord)
    if q:
        cond = sm.AftersaleRecord.order_no.contains(q) | sm.AftersaleRecord.customer_name.contains(q)
        stmt = stmt.where(cond)
        count_stmt = count_stmt.where(cond)
    if status:
        stmt = stmt.where(sm.AftersaleRecord.status == status)
        count_stmt = count_stmt.where(sm.AftersaleRecord.status == status)
    total = (await db.scalar(count_stmt)) or 0
    rows = (
        await db.scalars(
            stmt.order_by(sm.AftersaleRecord.id.desc()).offset((page - 1) * page_size).limit(page_size)
        )
    ).all()
    items = [
        {
            "id": r.id,
            "order_no": r.order_no,
            "customer_name": r.customer_name,
            "customer_contact": r.customer_contact,
            "problem_type": r.problem_type,
            "description": r.description,
            "result": r.result,
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
    return Page(items=items, total=total, page=page, page_size=page_size)


@router.post("/aftersales", response_model=dict)
async def create_aftersale(
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: SessionUser = Depends(perm("service.create")),
):
    obj = sm.AftersaleRecord(
        order_no=body.get("order_no"),
        customer_name=body.get("customer_name"),
        customer_contact=body.get("customer_contact"),
        problem_type=body.get("problem_type") or "其他",
        description=body.get("description") or "",
        result=body.get("result"),
        status=body.get("status") or "pending",
        handler_id=user.uid,
    )
    db.add(obj)
    await db.flush()
    await audit_log(db, user.uid, "service.aftersale", "create", str(obj.id))
    await db.commit()
    return {"id": obj.id}


@router.patch("/aftersales/{aid}", response_model=Ok)
async def update_aftersale(
    aid: int,
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: SessionUser = Depends(perm("service.update")),
):
    r = await db.get(sm.AftersaleRecord, aid)
    if not r:
        raise NotFoundError("记录不存在")
    for k in ("order_no", "customer_name", "customer_contact", "problem_type", "description", "result", "status"):
        if k in body:
            setattr(r, k, body[k])
    await db.commit()
    return Ok(detail="已更新")


# ---------- 发票 ----------


@router.get("/invoices", response_model=Page[dict])
async def list_invoices(
    q: str | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: SessionUser = Depends(perm("service.list")),
):
    stmt = select(sm.Invoice)
    count_stmt = select(func.count()).select_from(sm.Invoice)
    if q:
        cond = sm.Invoice.invoice_no.contains(q)
        stmt = stmt.where(cond)
        count_stmt = count_stmt.where(cond)
    if status:
        stmt = stmt.where(sm.Invoice.status == status)
        count_stmt = count_stmt.where(sm.Invoice.status == status)
    total = (await db.scalar(count_stmt)) or 0
    rows = (
        await db.scalars(
            stmt.order_by(sm.Invoice.id.desc()).offset((page - 1) * page_size).limit(page_size)
        )
    ).all()
    items = [
        {
            "id": r.id,
            "invoice_no": r.invoice_no,
            "invoice_type": r.invoice_type,
            "amount": str(r.amount),
            "supplier_id": r.supplier_id,
            "invoice_date": r.invoice_date.isoformat() if r.invoice_date else None,
            "remark": r.remark,
            "status": r.status,
            "attachment_keys": r.attachment_keys or [],
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
    return Page(items=items, total=total, page=page, page_size=page_size)


@router.post("/invoices", response_model=dict)
async def create_invoice(
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: SessionUser = Depends(perm("service.create")),
):
    from decimal import Decimal

    from datetime import date

    inv_date = None
    if body.get("invoice_date"):
        inv_date = date.fromisoformat(body["invoice_date"])
    obj = sm.Invoice(
        invoice_no=body.get("invoice_no") or "",
        invoice_type=body.get("invoice_type") or "普票",
        amount=Decimal(str(body.get("amount") or "0")),
        supplier_id=body.get("supplier_id"),
        invoice_date=inv_date,
        remark=body.get("remark"),
        created_by=user.uid,
    )
    db.add(obj)
    await db.flush()
    await audit_log(db, user.uid, "service.invoice", "create", str(obj.id))
    await db.commit()
    return {"id": obj.id}


@router.post("/invoices/{iid}/upload", response_model=Ok)
async def upload_invoice_attachment(
    iid: int,
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: SessionUser = Depends(perm("service.invoice_upload")),
):
    """简化：前端先传文件到通用上传接口拿到 keys，再调此接口绑定"""
    inv = await db.get(sm.Invoice, iid)
    if not inv:
        raise NotFoundError("发票不存在")
    keys = list(inv.attachment_keys or [])
    keys.extend(body.get("files") or [])
    inv.attachment_keys = keys
    inv.status = "uploaded"
    # 停掉该发票提醒
    rems = (
        await db.scalars(
            select(sm.Reminder).where(sm.Reminder.rtype == "invoice", sm.Reminder.ref_id == iid)
        )
    ).all()
    for rem in rems:
        if rem.status in ("pending", "delivered"):
            rem.status = "read"
    await audit_log(db, user.uid, "service.invoice", "upload", str(iid))
    await db.commit()
    return Ok(detail="已回传")


@router.get("/reminders")
async def list_reminders(
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: SessionUser = Depends(perm("service.list")),
):
    stmt = select(sm.Reminder)
    if status:
        stmt = stmt.where(sm.Reminder.status == status)
    rows = (await db.scalars(stmt.order_by(sm.Reminder.id.desc()).limit(100))).all()
    return [
        {
            "id": r.id,
            "rtype": r.rtype,
            "ref_id": r.ref_id,
            "title": r.title,
            "body": r.body,
            "status": r.status,
            "retry_count": r.retry_count,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@router.get("/reminder-count")
async def reminder_count(
    db: AsyncSession = Depends(get_db),
    user: SessionUser = Depends(perm("workbench")),
):
    n = await db.scalar(
        select(func.count()).select_from(sm.Reminder).where(sm.Reminder.status.in_(["pending", "delivered"]))
    )
    return {"total": int(n or 0)}
