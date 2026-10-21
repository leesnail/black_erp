# -*- coding: utf-8 -*-
"""生产环境数据库初始化：建表 + 种子数据（幂等）

用法（在 backend/ 目录下）:
    python -m app.init_db
"""
import asyncio


async def main() -> None:
    from app.core.database import Base, engine, SessionLocal  # noqa: F401 确保模型注册
    from app.modules.admin import models  # noqa: F401
    from app.modules.calc import models  # noqa: F401
    from app.modules.master import models  # noqa: F401
    from app.modules.report import models  # noqa: F401
    from app.modules.service import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    from app.seed import run_seed

    await run_seed()
    await engine.dispose()
    print("init_db done: tables created (idempotent), seed applied")


if __name__ == "__main__":
    asyncio.run(main())
