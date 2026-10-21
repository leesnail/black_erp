# -*- coding: utf-8 -*-
"""auth 输入输出 schema"""
from pydantic import BaseModel, Field


class LoginIn(BaseModel):
    account: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    id: int
    account: str
    display_name: str
    role: str
    perms: list[str]
    csrf_token: str


class ChangePasswordIn(BaseModel):
    old_password: str
    new_password: str = Field(min_length=8, max_length=64)
