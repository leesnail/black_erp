# -*- coding: utf-8 -*-
# 必须先导入 celery_app，让 shared_task 绑定到本应用的 broker
from app.tasks.celery_app import celery_app  # noqa: F401
from app.tasks import calc, report  # noqa: F401
