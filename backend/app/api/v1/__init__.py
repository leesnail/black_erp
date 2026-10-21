# -*- coding: utf-8 -*-
"""API v1 路由聚合"""
from fastapi import APIRouter

from app.api.v1 import admin, auth, calc, master, report, service

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(admin.router)
api_router.include_router(master.router)
api_router.include_router(calc.router)
api_router.include_router(service.router)
api_router.include_router(report.router)
