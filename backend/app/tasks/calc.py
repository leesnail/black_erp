# -*- coding: utf-8 -*-
"""calc Celery 任务"""
import asyncio
import logging
from datetime import datetime

from celery import shared_task

from app.common.csv_parser import iter_orders, parse_chunk
from app.core.database import SessionLocal
from app.core.redis import redis
from app.modules.calc import models as cm
from app.modules.calc import service as calc_svc
from app.modules.master import models as mm

logger = logging.getLogger(__name__)


_loop: asyncio.AbstractEventLoop | None = None


def _run_async(coro):
    """worker 进程内复用同一个事件循环，避免连接池跨 loop 失效"""
    global _loop
    if _loop is None or _loop.is_closed():
        _loop = asyncio.new_event_loop()
    return _loop.run_until_complete(coro)


async def _run_calc_async(batch_id: int) -> None:
    async with SessionLocal() as db:
        batch = await db.get(cm.Batch, batch_id)
        if not batch:
            logger.error("batch %s not found", batch_id)
            return
        if batch.status not in ("pending", "failed"):
            logger.info("batch %s status=%s skip", batch_id, batch.status)
            return

        lock_key = f"batch:lock:{batch_id}"
        if not await redis.set(lock_key, "1", nx=True, ex=3600):
            logger.warning("batch %s already running", batch_id)
            return

        try:
            batch.status = "running"
            batch.err_msg = None
            await db.commit()

            ctx = await calc_svc.load_context(db, batch.shop_id)

            # 若 source_key 是本地路径（开发直接传路径）或 uploads 相对路径
            from app.core.config import settings

            path = str(settings.upload_path / batch.source_key)
            all_results = []
            parse_errors: list[dict] = []
            total = no_ship = aftersale = qty_invalid = 0

            for chunk in iter_orders(path):
                pr = parse_chunk(chunk)
                total += pr.total
                no_ship += pr.no_ship
                aftersale += pr.aftersale
                qty_invalid += pr.qty_invalid
                parse_errors.extend(pr.errors[:50])
                for raw in pr.rows:
                    all_results.append(calc_svc.process_line(raw, ctx))

            await calc_svc.bulk_insert_lines(db, batch.id, all_results)
            stats = calc_svc.aggregate(all_results)
            stats.update(
                {
                    "total_rows": total,
                    "no_ship_skip": no_ship,
                    "aftersale": aftersale,
                    "qty_invalid": qty_invalid,
                    "parse_errors": parse_errors[:20],
                }
            )
            batch.stats = stats
            batch.status = "success"
            batch.finished_at = datetime.utcnow()
            await db.commit()
            logger.info("batch %s done stats=%s", batch_id, stats)
        except Exception as e:
            logger.exception("batch %s failed", batch_id)
            batch.status = "failed"
            batch.err_msg = str(e)[:2000]
            await db.commit()
            raise
        finally:
            await redis.delete(lock_key)


@shared_task(name="app.tasks.calc.run_calc", bind=True, max_retries=3)
def run_calc(self, batch_id: int):
    try:
        _run_async(_run_calc_async(batch_id))
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)
