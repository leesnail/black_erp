# -*- coding: utf-8 -*-
"""master 公共服务函数"""
from app.core.redis import redis


async def next_spec_code() -> str:
    n = await redis.incr("spec:seq")
    return f"SP{n:06d}"
