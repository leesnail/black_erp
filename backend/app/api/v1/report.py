# -*- coding: utf-8 -*-
"""报表路由：驾驶舱 / 日报"""
from datetime import date, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import SessionUser, perm
from app.modules.calc import models as cm
from app.modules.master import models as mm
from app.modules.report import models as rm

router = APIRouter(prefix="/report", tags=["report"])


@router.get("/cockpit/overview")
async def cockpit_overview(
    shop_id: int | None = None,
    period: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: SessionUser = Depends(perm("report.list")),
):
    stmt = select(cm.Batch).where(cm.Batch.status.in_(["success", "settled"]))
    if shop_id:
        stmt = stmt.where(cm.Batch.shop_id == shop_id)
    if period:
        stmt = stmt.where(cm.Batch.period == period)
    batches = (await db.scalars(stmt.order_by(cm.Batch.id.desc()).limit(500))).all()

    by_shop: dict[int, dict] = {}
    for b in batches:
        s = b.stats or {}
        acc = by_shop.setdefault(
            b.shop_id,
            {"income": Decimal("0"), "cost": Decimal("0"), "ship": 0, "aftersale": 0, "unmatched": 0},
        )
        acc["income"] += Decimal(str(s.get("income_total") or 0))
        acc["cost"] += Decimal(str(s.get("cost_total") or 0))
        acc["ship"] += int(s.get("ship_count") or 0)
        acc["aftersale"] += int(s.get("aftersale") or 0)
        acc["unmatched"] += int(s.get("unmatched") or 0)

    shops = {s.id: s for s in (await db.scalars(select(mm.Shop))).all()}
    shop_rows = []
    total_income = total_cost = Decimal("0")
    total_ship = total_unmatched = 0
    for sid, acc in by_shop.items():
        profit = acc["income"] - acc["cost"]
        total_income += acc["income"]
        total_cost += acc["cost"]
        total_ship += acc["ship"]
        total_unmatched += acc["unmatched"]
        shop_rows.append(
            {
                "shop_id": sid,
                "shop_name": shops[sid].name if sid in shops else str(sid),
                "income": str(acc["income"].quantize(Decimal("0.01"))),
                "cost": str(acc["cost"].quantize(Decimal("0.01"))),
                "profit": str(profit.quantize(Decimal("0.01"))),
                "ship_count": acc["ship"],
                "aftersale": acc["aftersale"],
            }
        )
    shop_rows.sort(key=lambda x: Decimal(x["profit"]), reverse=True)

    # 近 6 月趋势（按 batch.period 聚合）
    trend: dict[str, Decimal] = {}
    for b in batches:
        if b.period:
            s = b.stats or {}
            trend[b.period] = trend.get(b.period, Decimal("0")) + Decimal(str(s.get("profit") or 0))
    trend_rows = [
        {"period": p, "profit": str(v.quantize(Decimal("0.01")))}
        for p, v in sorted(trend.items())
        if p
    ][-6:]

    return {
        "income_total": str(total_income.quantize(Decimal("0.01"))),
        "cost_total": str(total_cost.quantize(Decimal("0.01"))),
        "profit_total": str((total_income - total_cost).quantize(Decimal("0.01"))),
        "ship_count": total_ship,
        "unmatched_backlog": total_unmatched,
        "shops": shop_rows,
        "trend": trend_rows,
    }


@router.get("/daily-reports")
async def daily_reports(
    start: str | None = None,
    end: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: SessionUser = Depends(perm("report.list")),
):
    stmt = select(rm.DailyReport, mm.Shop.name).join(mm.Shop, rm.DailyReport.shop_id == mm.Shop.id, isouter=True)
    if start:
        stmt = stmt.where(rm.DailyReport.report_date >= date.fromisoformat(start))
    if end:
        stmt = stmt.where(rm.DailyReport.report_date <= date.fromisoformat(end))
    rows = (await db.execute(stmt.order_by(rm.DailyReport.report_date.desc(), mm.Shop.name).limit(500))).all()
    return [
        {
            "id": r.id,
            "shop_name": n,
            "report_date": r.report_date.isoformat(),
            "order_count": r.order_count,
            "income_total": str(r.income_total),
            "cost_total": str(r.cost_total),
            "profit": str(r.profit),
        }
        for r, n in rows
    ]
