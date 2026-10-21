# -*- coding: utf-8 -*-
"""公共 Pydantic 响应模型"""
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


class Ok(BaseModel):
    ok: bool = True
    detail: str = ""
