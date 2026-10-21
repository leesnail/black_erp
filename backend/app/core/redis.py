# -*- coding: utf-8 -*-
"""Redis 客户端（会话/锁/序列）"""
import json
from typing import Any

import redis.asyncio as aioredis

from app.core.config import settings

redis: aioredis.Redis = aioredis.from_url(settings.redis_url, decode_responses=True)


def dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, default=str)


def loads(s: str | bytes | None) -> Any:
    if s is None:
        return None
    return json.loads(s)
