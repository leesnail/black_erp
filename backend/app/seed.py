# -*- coding: utf-8 -*-
"""种子数据：角色、管理员账号、地区规则、示例店铺"""
import logging

from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.modules.admin.models import Role, User
from app.modules.admin.perm_matrix import ROLE_PERMS
from app.modules.master.models import RegionRule, Shop

logger = logging.getLogger(__name__)


async def run_seed() -> None:
    async with SessionLocal() as db:
        # 角色
        for name, conf in ROLE_PERMS.items():
            role = await db.scalar(select(Role).where(Role.name == name))
            if not role:
                db.add(
                    Role(
                        name=name,
                        display_name=conf["display_name"],
                        default_perms=conf["perms"],
                    )
                )
        await db.flush()

        # 管理员
        admin_role = await db.scalar(select(Role).where(Role.name == "admin"))
        admin = await db.scalar(select(User).where(User.account == "admin"))
        if not admin:
            db.add(
                User(
                    account="admin",
                    password_hash=hash_password("Admin@12345"),
                    display_name="系统管理员",
                    role_id=admin_role.id,
                )
            )
            logger.info("seeded admin account: admin / Admin@12345")

        # 财务示例账号
        fin_role = await db.scalar(select(Role).where(Role.name == "fin"))
        fin = await db.scalar(select(User).where(User.account == "finance"))
        if not fin:
            db.add(
                User(
                    account="finance",
                    password_hash=hash_password("Fin@12345"),
                    display_name="财务小王",
                    role_id=fin_role.id,
                )
            )
            logger.info("seeded finance account: finance / Fin@12345")

        # 地区规则预置
        r1 = await db.scalar(select(RegionRule).where(RegionRule.name == "偏远+4"))
        if not r1:
            db.add(
                RegionRule(
                    name="偏远+4",
                    provinces=["海南", "青海", "内蒙古", "宁夏", "甘肃"],
                    amount=4,
                    unit="per_piece",
                )
            )
        r2 = await db.scalar(select(RegionRule).where(RegionRule.name == "偏远+20"))
        if not r2:
            db.add(
                RegionRule(
                    name="偏远+20",
                    provinces=["新疆", "西藏"],
                    amount=20,
                    unit="per_piece",
                )
            )

        # 示例店铺
        shop = await db.scalar(select(Shop).where(Shop.name == "誉恒"))
        if not shop:
            db.add(Shop(name="誉恒", full_name="誉恒旗舰店"))

        await db.commit()
        logger.info("seed done")
