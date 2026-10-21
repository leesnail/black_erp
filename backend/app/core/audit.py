# -*- coding: utf-8 -*-
"""操作审计日志写入"""
import json
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession


async def audit_log(
    db: AsyncSession,
    user_id: int | None,
    module: str,
    action: str,
    target: str = "",
    before: Any = None,
    after: Any = None,
    ip: str | None = None,
) -> None:
    from app.modules.admin.models import AuditLog

    def _ser(v: Any) -> str | None:
        if v is None:
            return None
        try:
            return json.dumps(v, ensure_ascii=False, default=str)
        except Exception:
            return str(v)

    db.add(
        AuditLog(
            user_id=user_id,
            module=module,
            action=action,
            target=target,
            before=_ser(before),
            after=_ser(after),
            ip=ip,
        )
    )
