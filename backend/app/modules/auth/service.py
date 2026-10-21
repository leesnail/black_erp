# -*- coding: utf-8 -*-
"""auth 服务：登录校验、有效权限计算"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BizError
from app.core.security import SessionUser, verify_password
from app.modules.admin.models import Role, User
from app.modules.admin.perm_matrix import ROLE_PERMS


async def verify_login(db: AsyncSession, account: str, password: str) -> User:
    user = await db.scalar(select(User).where(User.account == account))
    if not user or user.status != "active":
        raise BizError("账号或密码错误")
    if not verify_password(password, user.password_hash):
        raise BizError("账号或密码错误")
    return user


async def effective_perms(db: AsyncSession, user: User) -> list[str]:
    """角色默认权限 ⊕ 个人模块覆盖"""
    role = await db.get(Role, user.role_id)
    base = list((role.default_perms or [])) if role else []
    overrides: dict = user.module_overrides or {}

    # 覆盖语义: {"master.spec": "read"} 增加只读；{"service": false} 移除
    result = set(base)
    for mod, val in overrides.items():
        if val is False or val == "none":
            # 移除该模块前缀的所有权限
            result = {p for p in result if not p.startswith(mod)}
        elif val == "read":
            result.add(f"{mod}.list")
            result.add(f"{mod}.export")
        elif val == "write":
            for a in ("list", "create", "update", "export"):
                result.add(f"{mod}.{a}")
    return sorted(result)


def build_session_user(user: User, perms: list[str], csrf: str) -> SessionUser:
    role_name = "user"
    # 从 ROLE_PERMS 反查 role key（User 只存 role_id）
    return SessionUser(
        uid=user.id,
        account=user.account,
        display_name=user.display_name,
        role=role_name,
        perms=perms,
        csrf=csrf,
    )


async def load_role_name(db: AsyncSession, role_id: int) -> str:
    role = await db.get(Role, role_id)
    return role.name if role else "user"
