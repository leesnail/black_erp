# -*- coding: utf-8 -*-
"""Celery 应用实例与 Beat 计划"""
from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

# 导入全部 ORM 模型，确保 worker 进程元数据完整（FK 解析依赖）
from app.modules.admin import models as _admin_models  # noqa: F401
from app.modules.calc import models as _calc_models  # noqa: F401
from app.modules.master import models as _master_models  # noqa: F401
from app.modules.report import models as _report_models  # noqa: F401
from app.modules.service import models as _service_models  # noqa: F401

celery_app = Celery("black_erp", broker=settings.celery_broker_url, backend=settings.redis_url)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    result_expires=86400,
    beat_schedule={
        "generate-daily-report": {
            "task": "app.tasks.report.generate_daily_report",
            "schedule": crontab(hour=9, minute=0),
        },
        "scan-invoice-reminders": {
            "task": "app.tasks.reminder.scan_invoice_reminders",
            "schedule": crontab(minute=0),  # 每小时
        },
        "cleanup-exports": {
            "task": "app.tasks.report.cleanup_exports",
            "schedule": crontab(hour=3, minute=0),
        },
    },
)

# 注册任务模块
celery_app.autodiscover_tasks(["app.tasks"])
