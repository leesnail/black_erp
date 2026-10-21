# -*- coding: utf-8 -*-
"""业务异常与全局处理器"""
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse


class BizError(Exception):
    """业务可读错误（前端 ElMessage.error(detail)）"""

    def __init__(self, detail: str, code: int = 400, status_code: int = 400):
        self.detail = detail
        self.code = code
        self.status_code = status_code
        super().__init__(detail)


class NotFoundError(BizError):
    def __init__(self, detail: str = "资源不存在"):
        super().__init__(detail, status_code=404)


class ConflictError(BizError):
    def __init__(self, detail: str = "数据冲突"):
        super().__init__(detail, status_code=409)


class ForbiddenError(BizError):
    def __init__(self, detail: str = "无权限"):
        super().__init__(detail, status_code=403)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(BizError)
    async def _(request: Request, exc: BizError):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail, "code": exc.code},
        )

    @app.exception_handler(Exception)
    async def _(request: Request, exc: Exception):
        # 生产环境不暴露堆栈；trace_id 由中间件注入
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "服务器内部错误", "code": 500},
        )
