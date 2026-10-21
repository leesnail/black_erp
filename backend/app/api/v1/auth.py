# -*- coding: utf-8 -*-
"""认证路由"""
from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.redis import redis
from app.core.security import (
    SESSION_COOKIE,
    create_session,
    current_user,
    destroy_session,
    hash_password,
    verify_password,
)
from app.modules.admin.models import User
from app.modules.auth import service as auth_service
from app.modules.auth.schemas import ChangePasswordIn, LoginIn, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=UserOut)
async def login(body: LoginIn, request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    user = await auth_service.verify_login(db, body.account, body.password)
    perms = await auth_service.effective_perms(db, user)
    role_name = await auth_service.load_role_name(db, user.role_id)
    sid, csrf = await create_session(
        user_id=user.id,
        account=user.account,
        display_name=user.display_name,
        role=role_name,
        perms=perms,
        ttl=settings.session_ttl_seconds,
    )
    response.set_cookie(
        SESSION_COOKIE,
        sid,
        httponly=True,
        samesite="lax",
        secure=settings.secure_cookie,
        max_age=settings.session_ttl_seconds,
    )
    return UserOut(
        id=user.id,
        account=user.account,
        display_name=user.display_name,
        role=role_name,
        perms=perms,
        csrf_token=csrf,
    )


@router.post("/logout")
async def logout(request: Request, response: Response):
    await destroy_session(request.cookies.get(SESSION_COOKIE))
    response.delete_cookie(SESSION_COOKIE)
    return {"ok": True}


@router.get("/me", response_model=UserOut)
async def me(request: Request, db: AsyncSession = Depends(get_db)):
    su = await current_user(request)
    user = await db.get(User, su.uid)
    if not user:
        from fastapi import HTTPException

        raise HTTPException(401, "用户不存在")
    # 会话里的 perms 可能过期；me 时重算一次保证覆盖即时生效
    perms = await auth_service.effective_perms(db, user)
    return UserOut(
        id=user.id,
        account=user.account,
        display_name=user.display_name,
        role=su.role,
        perms=perms,
        csrf_token=su.csrf,
    )


@router.post("/change-password")
async def change_password(
    body: ChangePasswordIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    su = await current_user(request)
    user = await db.get(User, su.uid)
    if not user or not verify_password(body.old_password, user.password_hash):
        from app.core.exceptions import BizError

        raise BizError("原密码错误")
    user.password_hash = hash_password(body.new_password)
    await db.commit()
    return {"ok": True}
