# -*- coding: utf-8 -*-
"""report / reminder Celery 任务占位（S4 完善）"""
import asyncio
import logging
from datetime import date, datetime, timedelta

from celery import shared_task
from sqlalchemy import select

from app.core.database import SessionLocal
from app.modules.calc import models as cm
from app.modules.master import models as mm
from app.modules.report import models as rm
from app.modules.service import models as sm

logger = logging.getLogger(__name__)

_loop: asyncio.AbstractEventLoop | None = None


def _run_async(coro):
    """worker 进程内复用同一个事件循环，避免连接池跨 loop 失效"""
    global _loop
    if _loop is None or _loop.is_closed():
        _loop = asyncio.new_event_loop()
    return _loop.run_until_complete(coro)


@shared_task(name="app.tasks.report.generate_daily_report")
def generate_daily_report(day: str | None = None):
    """按店铺聚合昨日已 success 批次 stats 写入 DailyReport（幂等）"""
    if day:
        target = date.fromisoformat(day)
    else:
        target = datetime.utcnow().date() - timedelta(days=1)

    async def _run():
        async with SessionLocal() as db:
            shops = (await db.scalars(select(mm.Shop).where(mm.Shop.status == "active"))).all()
            for shop in shops:
                batches = (
                    await db.scalars(
                        select(cm.Batch).where(
                            cm.Batch.shop_id == shop.id,
                            cm.Batch.status.in_(["success", "settled"]),
                            cm.Batch.created_at >= datetime.combine(target, datetime.min.time()),
                            cm.Batch.created_at < datetime.combine(target + timedelta(days=1), datetime.min.time()),
                        )
                    )
                ).all()
                if not batches:
                    continue
                income = sum(float((b.stats or {}).get("income_total") or 0) for b in batches)
                cost = sum(float((b.stats or {}).get("cost_total") or 0) for b in batches)
                orders = sum(int((b.stats or {}).get("ship_count") or 0) for b in batches)
                existing = await db.scalar(
                    select(rm.DailyReport).where(
                        rm.DailyReport.shop_id == shop.id, rm.DailyReport.report_date == target
                    )
                )
                if existing:
                    existing.order_count = orders
                    existing.income_total = income
                    existing.cost_total = cost
                    existing.profit = income - cost
                else:
                    db.add(
                        rm.DailyReport(
                            shop_id=shop.id,
                            report_date=target,
                            order_count=orders,
                            income_total=income,
                            cost_total=cost,
                            profit=income - cost,
                        )
                    )
            await db.commit()

    _run_async(_run())


@shared_task(name="app.tasks.reminder.scan_invoice_reminders")
def scan_invoice_reminders():
    """登记满 8 天且未回传的发票 → 提醒（站内）"""
    from datetime import timedelta as td

    cutoff = datetime.utcnow() - td(days=8)

    async def _run():
        async with SessionLocal() as db:
            invoices = (
                await db.scalars(
                    select(sm.Invoice).where(sm.Invoice.status == "pending", sm.Invoice.created_at <= cutoff)
                )
            ).all()
            for inv in invoices:
                exists = await db.scalar(
                    select(sm.Reminder).where(sm.Reminder.rtype == "invoice", sm.Reminder.ref_id == inv.id)
                )
                if exists and exists.status in ("delivered", "read"):
                    continue
                if exists:
                    exists.status = "pending"
                    exists.plan_at = datetime.utcnow()
                else:
                    db.add(
                        sm.Reminder(
                            rtype="invoice",
                            ref_id=inv.id,
                            title=f"发票 {inv.invoice_no} 待回传",
                            body=f"金额 {inv.amount}，请上传发票附件",
                            status="pending",
                            plan_at=datetime.utcnow(),
                        )
                    )
            await db.commit()

    _run_async(_run())


@shared_task(name="app.tasks.report.cleanup_exports")
def cleanup_exports():
    logger.info("cleanup exports placeholder")
