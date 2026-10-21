# -*- coding: utf-8 -*-
"""会话创建/校验、密码哈希、CSRF、权限依赖"""
import json
import secrets
from dataclasses import dataclass
from typing import Callable

from fastapi import Cookie, Depends, Header, Request
from passlib.context import CryptContext
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN

from app.core.redis import redis

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(raw: str) -> str:
    return pwd_context.hash(raw)


def verify_password(raw: str, hashed: str) -> bool:
    return pwd_context.verify(raw, hashed)


@dataclass
class SessionUser:
    uid: int
    account: str
    display_name: str
    role: str  # admin|boss|cs|po|op|fin
    perms: list[str]
    csrf: str

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


SESSION_COOKIE = "sid"


async def create_session(user_id: int, account: str, display_name: str,
                         role: str, perms: list[str], ttl: int) -> tuple[str, str]:
    sid = secrets.token_urlsafe(32)
    csrf = secrets.token_urlsafe(16)
    payload = {
        "uid": user_id,
        "account": account,
        "display_name": display_name,
        "role": role,
        "perms": perms,
        "csrf": csrf,
    }
    await redis.setex(f"session:{sid}", ttl, json.dumps(payload, ensure_ascii=False))
    return sid, csrf


async def destroy_session(sid: str | None) -> None:
    if sid:
        await redis.delete(f"session:{sid}")


async def load_session(sid: str | None) -> SessionUser | None:
    if not sid:
        return None
    raw = await redis.get(f"session:{sid}")
    if not raw:
        return None
    data = json.loads(raw)
    return SessionUser(**data)


async def current_user(request: Request) -> SessionUser:
    sid = request.cookies.get(SESSION_COOKIE)
    user = await load_session(sid)
    if not user:
        from fastapi import HTTPException

        raise HTTPException(HTTP_401_UNAUTHORIZED, "未登录或会话已过期")
    return user


async def check_csrf(
    request: Request,
    user: SessionUser = Depends(current_user),
    x_csrf_token: str | None = Header(default=None, alias="X-CSRF-Token"),
) -> None:
    """写操作双提交校验"""
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return
    if not x_csrf_token or x_csrf_token != user.csrf:
        from fastapi import HTTPException

        raise HTTPException(HTTP_403_FORBIDDEN, "CSRF 校验失败")


def perm(code: str) -> Callable:
    """权限依赖工厂：Depends(perm("calc.upload"))"""

    async def dep(user: SessionUser = Depends(current_user)) -> SessionUser:
        if user.is_admin:
            return user
        if code not in user.perms:
            from fastapi import HTTPException

            raise HTTPException(HTTP_403_FORBIDDEN, f"无权限: {code}")
        return user

    return dep


def any_perm(*codes: str) -> Callable:
    async def dep(user: SessionUser = Depends(current_user)) -> SessionUser:
        if user.is_admin:
            return user
        if not any(c in user.perms for c in codes):
            from fastapi import HTTPException

            raise HTTPException(HTTP_403_FORBIDDEN, "无权限")
        return user

    return dep
