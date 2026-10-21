# -*- coding: utf-8 -*-
"""财务核算路由"""
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.csv_parser import guess_shop, iter_orders, parse_chunk, normalize_title, split_product
from app.common.schemas import Ok, Page
from app.core.audit import audit_log
from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import BizError, ForbiddenError, NotFoundError
from app.core.security import SessionUser, perm
from app.modules.calc import models as cm
from app.modules.calc import service as calc_svc
from app.modules.calc.schemas import (
    BatchOut,
    IgnoreIn,
    LineOut,
    ManualMatchIn,
    PreviewOut,
    UnmatchedLineOut,
)
from app.modules.master import models as mm
from app.modules.master.service import next_spec_code

router = APIRouter(prefix="/calc", tags=["calc"])

MAX_UPLOAD = settings.max_upload_mb * 1024 * 1024


def _shop_name(db, shop_id) -> str:
    return ""


async def _batch_out(db: AsyncSession, b: cm.Batch) -> BatchOut:
    shop = await db.get(mm.Shop, b.shop_id)
    return BatchOut(
        id=b.id,
        shop_id=b.shop_id,
        shop_name=shop.name if shop else "",
        period=b.period,
        source_filename=b.source_filename,
        status=b.status,
        version=b.version,
        stats=b.stats or {},
        err_msg=b.err_msg,
        created_at=b.created_at,
    )


@router.post("/batches", status_code=202)
async def create_batch(
    file: UploadFile = File(...),
    shop_id: int | None = Form(default=None),
    period: str | None = Form(default=None),
    db: AsyncSession = Depends(get_db),
    user: SessionUser = Depends(perm("calc.upload")),
):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise BizError("仅支持 CSV 文件")

    content = await file.read()
    if len(content) > MAX_UPLOAD:
        raise BizError(f"文件超过 {settings.max_upload_mb}MB 限制", status_code=413)

    # 店铺识别
    shop = None
    if shop_id:
        shop = await db.get(mm.Shop, shop_id)
    if not shop:
        guess = guess_shop(file.filename)
        shop = await db.scalar(select(mm.Shop).where(mm.Shop.name == guess))
        if not shop:
            shop = mm.Shop(name=guess, full_name=guess)
            db.add(shop)
            await db.flush()

    # 期间默认当月
    from datetime import datetime

    period = period or datetime.utcnow().strftime("%Y-%m")

    # 保存原始文件
    safe_name = f"{shop.name}_{period}_{user.uid}_{file.filename}"
    dest = settings.upload_path / "imports" / safe_name
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(content)

    # 轻量预检（抽样前 2000 行统计 + 全量列校验）
    preview = PreviewOut(shop_name=shop.name)
    try:
        sample_n = 0
        for chunk in iter_orders(str(dest), chunksize=2000):
            pr = parse_chunk(chunk)
            preview.total += pr.total
            preview.no_ship_skip += pr.no_ship
            preview.aftersale += pr.aftersale
            preview.qty_invalid += pr.qty_invalid
            preview.errors.extend(pr.errors[:5])
            sample_n += pr.total
            if sample_n >= 2000:
                break
    except ValueError as e:
        raise BizError(str(e))

    batch = cm.Batch(
        shop_id=shop.id,
        period=period,
        source_filename=file.filename,
        source_key=f"imports/{safe_name}",
        status="pending",
        created_by=user.uid,
        stats={"preview": preview.model_dump()},
    )
    db.add(batch)
    await db.flush()
    await audit_log(db, user.uid, "calc", "upload", str(batch.id), after={"file": file.filename})
    await db.commit()

    # 入队
    from app.tasks.calc import run_calc

    run_calc.delay(batch.id)

    return {"batch_id": batch.id, "preview": preview, "status": "pending"}


@router.get("/batches", response_model=list[BatchOut])
async def list_batches(
    shop_id: int | None = None,
    status: str | None = None,
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    user: SessionUser = Depends(perm("calc.list")),
):
    stmt = select(cm.Batch)
    if shop_id:
        stmt = stmt.where(cm.Batch.shop_id == shop_id)
    if status:
        stmt = stmt.where(cm.Batch.status == status)
    rows = (await db.scalars(stmt.order_by(cm.Batch.id.desc()).limit(limit))).all()
    out = []
    for b in rows:
        out.append(await _batch_out(db, b))
    return out


@router.get("/batches/{bid}", response_model=BatchOut)
async def get_batch(
    bid: int,
    db: AsyncSession = Depends(get_db),
    user: SessionUser = Depends(perm("calc.list")),
):
    b = await db.get(cm.Batch, bid)
    if not b:
        raise NotFoundError("批次不存在")
    return await _batch_out(db, b)


@router.get("/batches/{bid}/summary")
async def get_summary(
    bid: int,
    db: AsyncSession = Depends(get_db),
    user: SessionUser = Depends(perm("calc.list")),
):
    b = await db.get(cm.Batch, bid)
    if not b:
        raise NotFoundError("批次不存在")
    shop = await db.get(mm.Shop, b.shop_id)
    stats = b.stats or {}
    return {
        "batch_id": b.id,
        "shop_name": shop.name if shop else "",
        "period": b.period,
        "version": b.version,
        "status": b.status,
        **stats,
    }


@router.get("/batches/{bid}/lines", response_model=Page[LineOut])
async def list_lines(
    bid: int,
    matched: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: SessionUser = Depends(perm("calc.list")),
):
    stmt = select(cm.OrderLine).where(cm.OrderLine.batch_id == bid)
    count_stmt = select(func.count()).select_from(cm.OrderLine).where(cm.OrderLine.batch_id == bid)
    if matched:
        stmt = stmt.where(cm.OrderLine.matched == matched)
        count_stmt = count_stmt.where(cm.OrderLine.matched == matched)
    total = (await db.scalar(count_stmt)) or 0
    rows = (
        await db.scalars(
            stmt.order_by(cm.OrderLine.id).offset((page - 1) * page_size).limit(page_size)
        )
    ).all()

    # 批量取 spec_code
    spec_ids = {r.spec_id for r in rows if r.spec_id}
    code_map: dict[int, str] = {}
    if spec_ids:
        specs = (await db.scalars(select(mm.Spec).where(mm.Spec.id.in_(spec_ids)))).all()
        code_map = {s.id: s.spec_code for s in specs}

    items = [
        LineOut(
            id=r.id,
            order_no=r.order_no,
            raw_product=r.raw_product,
            title=r.title,
            spec_text=r.spec_text,
            qty=r.qty,
            province=r.province,
            spec_id=r.spec_id,
            spec_code=code_map.get(r.spec_id) if r.spec_id else None,
            price_snapshot=r.price_snapshot,
            surcharge=r.surcharge,
            unit_cost=r.unit_cost,
            line_cost=r.line_cost,
            income=r.income,
            matched=r.matched,
            aftersale_status=r.aftersale_status,
            ignored=r.ignored,
        )
        for r in rows
    ]
    return Page(items=items, total=total, page=page, page_size=page_size)


@router.get("/batches/{bid}/unmatched", response_model=list[UnmatchedLineOut])
async def list_unmatched(
    bid: int,
    db: AsyncSession = Depends(get_db),
    user: SessionUser = Depends(perm("calc.list")),
):
    b = await db.get(cm.Batch, bid)
    if not b:
        raise NotFoundError("批次不存在")
    rows = (
        await db.scalars(
            select(cm.OrderLine)
            .where(cm.OrderLine.batch_id == bid, cm.OrderLine.matched == "none", cm.OrderLine.ignored == False)  # noqa: E712
            .limit(500)
        )
    ).all()
    ctx = await calc_svc.load_context(db, b.shop_id)
    out = []
    for r in rows:
        rec = await calc_svc.recommendations_for_line(db, r, ctx)
        out.append(
            UnmatchedLineOut(
                id=r.id,
                order_no=r.order_no,
                raw_product=r.raw_product,
                title=r.title,
                spec_text=r.spec_text,
                qty=r.qty,
                province=r.province,
                spec_id=r.spec_id,
                price_snapshot=r.price_snapshot,
                surcharge=r.surcharge,
                unit_cost=r.unit_cost,
                line_cost=r.line_cost,
                income=r.income,
                matched=r.matched,
                aftersale_status=r.aftersale_status,
                ignored=r.ignored,
                recommend=rec,
            )
        )
    return out


@router.post("/batches/{bid}/manual-match", response_model=Ok)
async def manual_match(
    bid: int,
    body: ManualMatchIn,
    db: AsyncSession = Depends(get_db),
    user: SessionUser = Depends(perm("calc.manual_match")),
):
    b = await db.get(cm.Batch, bid)
    if not b:
        raise NotFoundError("批次不存在")
    if b.status == "settled":
        raise ForbiddenError("批次已结算，不可回填")

    spec = await db.get(mm.Spec, body.spec_id)
    if not spec:
        raise BizError("规格不存在")

    lines = (
        await db.scalars(
            select(cm.OrderLine).where(cm.OrderLine.batch_id == bid, cm.OrderLine.id.in_(body.line_ids))
        )
    ).all()
    if not lines:
        raise BizError("未找到指定行")

    import datetime as dt
    from decimal import Decimal
    from sqlalchemy import func as sa_func

    from app.modules.master.models import CostPrice

    price = await db.scalar(
        select(CostPrice.price)
        .where(CostPrice.spec_id == body.spec_id)
        .order_by(CostPrice.effective_at.desc())
        .limit(1)
    )

    ctx = await calc_svc.load_context(db, b.shop_id)
    manual_count = 0
    for ln in lines:
        ln.spec_id = body.spec_id
        ln.matched = "manual"
        ln.price_snapshot = price
        surcharge = ctx.region_surcharge(ln.province or "")
        ln.surcharge = surcharge
        if price is not None:
            ln.unit_cost = price + surcharge
            ln.line_cost = (ln.unit_cost * ln.qty).quantize(Decimal("0.01"))
        else:
            ln.unit_cost = None
            ln.line_cost = None
        manual_count += 1

        # 沉淀 MatchRule
        title_norm = normalize_title(ln.title or split_product(ln.raw_product)[0])
        spec_text = ln.spec_text or ""
        existing = await db.scalar(
            select(cm.MatchRule).where(
                cm.MatchRule.shop_id == b.shop_id,
                cm.MatchRule.title_norm == title_norm,
                cm.MatchRule.spec_text == spec_text,
            )
        )
        if existing:
            existing.spec_id = body.spec_id
        else:
            db.add(
                cm.MatchRule(
                    shop_id=b.shop_id,
                    title_norm=title_norm,
                    spec_text=spec_text,
                    spec_id=body.spec_id,
                    created_by=user.uid,
                )
            )

        # 回填同文本其他未匹配行
        twins = (
            await db.scalars(
                select(cm.OrderLine).where(
                    cm.OrderLine.batch_id == bid,
                    cm.OrderLine.matched == "none",
                    cm.OrderLine.ignored == False,  # noqa: E712
                    cm.OrderLine.id != ln.id,
                )
            )
        ).all()
        for t in twins:
            t_norm = normalize_title(t.title or split_product(t.raw_product)[0])
            if t_norm == title_norm and (t.spec_text or "") == spec_text:
                t.spec_id = body.spec_id
                t.matched = "manual"
                t.price_snapshot = price
                t.surcharge = surcharge
                if price is not None:
                    t.unit_cost = price + surcharge
                    t.line_cost = (t.unit_cost * t.qty).quantize(Decimal("0.01"))
                manual_count += 1

    # 更新 stats（含重算成本/利润，保证 summary 即时正确）
    stats = dict(b.stats or {})
    from decimal import Decimal as _D

    agg = await db.execute(
        select(
            sa_func.count(),
            sa_func.coalesce(sa_func.sum(cm.OrderLine.line_cost), 0),
            sa_func.coalesce(sa_func.sum(cm.OrderLine.income), 0),
        ).where(
            cm.OrderLine.batch_id == bid,
            cm.OrderLine.ignored == False,  # noqa: E712
        )
    )
    cnt, cost_sum, income_sum = agg.one()
    unmatched_now = await db.scalar(
        select(sa_func.count())
        .select_from(cm.OrderLine)
        .where(cm.OrderLine.batch_id == bid, cm.OrderLine.matched == "none", cm.OrderLine.ignored == False)  # noqa: E712
    )
    stats["unmatched"] = int(unmatched_now or 0)
    stats["matched_manual"] = int(stats.get("matched_manual") or 0) + manual_count
    stats["ship_count"] = int(cnt or 0)
    stats["cost_total"] = str(_D(str(cost_sum)).quantize(_D("0.01")))
    stats["income_total"] = str(_D(str(income_sum)).quantize(_D("0.01")))
    stats["profit"] = str((_D(str(income_sum)) - _D(str(cost_sum))).quantize(_D("0.01")))
    b.stats = stats

    await audit_log(db, user.uid, "calc", "manual_match", str(bid), after={"lines": body.line_ids, "spec": spec.spec_code})
    await db.commit()
    return Ok(detail=f"已指定 {manual_count} 行并沉淀匹配规则")


@router.post("/batches/{bid}/ignore", response_model=Ok)
async def ignore_lines(
    bid: int,
    body: IgnoreIn,
    db: AsyncSession = Depends(get_db),
    user: SessionUser = Depends(perm("calc.ignore")),
):
    b = await db.get(cm.Batch, bid)
    if not b:
        raise NotFoundError("批次不存在")
    lines = (
        await db.scalars(
            select(cm.OrderLine).where(cm.OrderLine.batch_id == bid, cm.OrderLine.id.in_(body.line_ids))
        )
    ).all()
    for ln in lines:
        ln.ignored = True
        ln.ignore_reason = body.reason
    # 同步 stats.unmatched
    from sqlalchemy import func as _func

    stats = dict(b.stats or {})
    unmatched_now = await db.scalar(
        select(_func.count())
        .select_from(cm.OrderLine)
        .where(cm.OrderLine.batch_id == bid, cm.OrderLine.matched == "none", cm.OrderLine.ignored == False)  # noqa: E712
    )
    stats["unmatched"] = int(unmatched_now or 0)
    b.stats = stats
    await audit_log(db, user.uid, "calc", "ignore", str(bid), after={"count": len(lines), "reason": body.reason})
    await db.commit()
    return Ok(detail=f"已忽略 {len(lines)} 行")


@router.post("/batches/{bid}/recalc", response_model=BatchOut)
async def recalc(
    bid: int,
    db: AsyncSession = Depends(get_db),
    user: SessionUser = Depends(perm("calc.recalc")),
):
    old = await db.get(cm.Batch, bid)
    if not old:
        raise NotFoundError("批次不存在")
    new = cm.Batch(
        shop_id=old.shop_id,
        period=old.period,
        source_filename=old.source_filename,
        source_key=old.source_key,
        status="pending",
        version=old.version + 1,
        created_by=user.uid,
    )
    db.add(new)
    await db.flush()
    await audit_log(db, user.uid, "calc", "recalc", str(new.id), before={"from": bid, "v": old.version})
    await db.commit()

    from app.tasks.calc import run_calc

    run_calc.delay(new.id)
    await db.refresh(new)
    return await _batch_out(db, new)


@router.get("/unmatched-total")
async def unmatched_total(
    db: AsyncSession = Depends(get_db),
    user: SessionUser = Depends(perm("calc.list")),
):
    """工作台角标：所有非 settled 批次未匹配总数"""
    from sqlalchemy import and_

    total = await db.scalar(
        select(func.count())
        .select_from(cm.OrderLine)
        .join(cm.Batch, cm.OrderLine.batch_id == cm.Batch.id)
        .where(
            cm.OrderLine.matched == "none",
            cm.OrderLine.ignored == False,  # noqa: E712
            cm.Batch.status.in_(["success"]),
        )
    )
    return {"total": int(total or 0)}
