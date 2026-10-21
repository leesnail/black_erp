# -*- coding: utf-8 -*-
"""系统管理路由"""
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.schemas import Ok, Page
from app.core.audit import audit_log
from app.core.database import get_db
from app.core.exceptions import BizError, NotFoundError
from app.core.security import SessionUser, hash_password, perm
from app.modules.admin.models import AuditLog, Role, User
from app.modules.admin.perm_matrix import ROLE_PERMS
from app.modules.master import models as mm

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/perm-matrix")
async def get_perm_matrix(
    db: AsyncSession = Depends(get_db),
    user: SessionUser = Depends(perm("admin.list")),
):
    roles = (await db.scalars(select(Role))).all()
    return [
        {
            "name": r.name,
            "display_name": r.display_name,
            "default_perms": r.default_perms or [],
        }
        for r in roles
    ]


@router.get("/accounts", response_model=Page[dict])
async def list_accounts(
    q: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: SessionUser = Depends(perm("admin.list")),
):
    stmt = select(User, Role.name.label("role_name"), Role.display_name.label("role_display")).join(
        Role, User.role_id == Role.id
    )
    count_stmt = select(func.count()).select_from(User)
    if q:
        cond = User.account.contains(q) | User.display_name.contains(q)
        stmt = stmt.where(cond)
        count_stmt = count_stmt.where(cond)
    total = (await db.scalar(count_stmt)) or 0
    rows = (
        await db.execute(
            stmt.order_by(User.id).offset((page - 1) * page_size).limit(page_size)
        )
    ).all()
    items = [
        {
            "id": u.id,
            "account": u.account,
            "display_name": u.display_name,
            "role": rn,
            "role_display": rd,
            "status": u.status,
            "module_overrides": u.module_overrides or {},
        }
        for u, rn, rd in rows
    ]
    return Page(items=items, total=total, page=page, page_size=page_size)


@router.post("/accounts", response_model=dict)
async def create_account(
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: SessionUser = Depends(perm("admin.create")),
):
    account = (body.get("account") or "").strip()
    password = body.get("password") or ""
    role_name = body.get("role") or "cs"
    if not account or len(password) < 8:
        raise BizError("账号不能为空，密码至少 8 位")
    exists = await db.scalar(select(User).where(User.account == account))
    if exists:
        raise BizError("账号已存在")
    role = await db.scalar(select(Role).where(Role.name == role_name))
    if not role:
        raise BizError(f"角色不存在: {role_name}")
    u = User(
        account=account,
        password_hash=hash_password(password),
        display_name=body.get("display_name") or account,
        role_id=role.id,
        module_overrides=body.get("module_overrides") or {},
    )
    db.add(u)
    await db.flush()
    await audit_log(db, user.uid, "admin.account", "create", account)
    await db.commit()
    return {"id": u.id, "account": u.account}


@router.patch("/accounts/{uid}/status", response_model=Ok)
async def toggle_account(
    uid: int,
    status: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: SessionUser = Depends(perm("admin.update")),
):
    if status not in ("active", "disabled"):
        raise BizError("status 无效")
    u = await db.get(User, uid)
    if not u:
        raise NotFoundError("账号不存在")
    if u.id == user.uid and status == "disabled":
        raise BizError("不能停用自己")
    u.status = status
    await audit_log(db, user.uid, "admin.account", status, u.account)
    await db.commit()
    return Ok(detail="已更新")


@router.patch("/accounts/{uid}/perm", response_model=Ok)
async def assign_perms(
    uid: int,
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: SessionUser = Depends(perm("admin.perm_assign")),
):
    """module_overrides: {"master.spec": "read"|"write"|false}"""
    u = await db.get(User, uid)
    if not u:
        raise NotFoundError("账号不存在")
    before = u.module_overrides or {}
    u.module_overrides = body.get("module_overrides") or {}
    await audit_log(db, user.uid, "admin.account", "perm_assign", u.account, before=before, after=u.module_overrides)
    await db.commit()
    return Ok(detail="权限已更新")


@router.patch("/accounts/{uid}/reset-password", response_model=Ok)
async def reset_password(
    uid: int,
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: SessionUser = Depends(perm("admin.update")),
):
    u = await db.get(User, uid)
    if not u:
        raise NotFoundError("账号不存在")
    pwd = body.get("password") or ""
    if len(pwd) < 8:
        raise BizError("密码至少 8 位")
    u.password_hash = hash_password(pwd)
    await audit_log(db, user.uid, "admin.account", "reset_password", u.account)
    await db.commit()
    return Ok(detail="密码已重置")


@router.get("/audit-logs", response_model=Page[dict])
async def list_logs(
    module: str | None = None,
    action: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: SessionUser = Depends(perm("admin.list")),
):
    stmt = select(AuditLog, User.account, User.display_name).join(User, AuditLog.user_id == User.id, isouter=True)
    count_stmt = select(func.count()).select_from(AuditLog)
    if module:
        stmt = stmt.where(AuditLog.module == module)
        count_stmt = count_stmt.where(AuditLog.module == module)
    if action:
        stmt = stmt.where(AuditLog.action == action)
        count_stmt = count_stmt.where(AuditLog.action == action)
    total = (await db.scalar(count_stmt)) or 0
    rows = (
        await db.execute(
            stmt.order_by(AuditLog.id.desc()).offset((page - 1) * page_size).limit(page_size)
        )
    ).all()
    items = [
        {
            "id": log.id,
            "user_id": log.user_id,
            "account": acc,
            "display_name": dn,
            "module": log.module,
            "action": log.action,
            "target": log.target,
            "before": log.before,
            "after": log.after,
            "ip": log.ip,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log, acc, dn in rows
    ]
    return Page(items=items, total=total, page=page, page_size=page_size)


@router.get("/region-rules")
async def list_rules(
    db: AsyncSession = Depends(get_db),
    user: SessionUser = Depends(perm("admin.list")),
):
    rows = (await db.scalars(select(mm.RegionRule))).all()
    return [
        {
            "id": r.id,
            "name": r.name,
            "provinces": r.provinces,
            "amount": str(r.amount),
            "unit": r.unit,
            "status": r.status,
        }
        for r in rows
    ]


@router.patch("/region-rules/{rid}", response_model=Ok)
async def update_rule(
    rid: int,
    body: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: SessionUser = Depends(perm("admin.update")),
):
    r = await db.get(mm.RegionRule, rid)
    if not r:
        raise NotFoundError("规则不存在")
    before = {"amount": str(r.amount), "provinces": r.provinces}
    if "amount" in body:
        from decimal import Decimal

        r.amount = Decimal(str(body["amount"]))
    if "provinces" in body:
        r.provinces = body["provinces"]
    if "status" in body:
        r.status = body["status"]
    await audit_log(db, user.uid, "admin.region_rule", "update", str(rid), before=before)
    await db.commit()
    return Ok(detail="规则已更新（仅影响之后的计算）")
