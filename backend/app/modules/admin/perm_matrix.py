# -*- coding: utf-8 -*-
"""权限矩阵定义（种子数据）"""
# 权限码 = 模块[.子模块].动作
# 动作: list get create update delete export + 特殊

ROLE_PERMS: dict[str, dict] = {
    "admin": {
        "display_name": "管理员",
        "perms": ["*"],  # 全部
    },
    "boss": {
        "display_name": "老板",
        "perms": [
            "workbench",
            "master.supplier.list", "master.supplier.export",
            "master.spec.list", "master.spec.export",
            "master.shop_product.list",
            "calc.list", "calc.export",
            "report.list", "report.export",
            "roi.list",
        ],
    },
    "cs": {
        "display_name": "客服",
        "perms": [
            "workbench",
            "service.list", "service.create", "service.update", "service.export",
            "service.invoice_upload",
            "master.supplier.list", "master.supplier.create", "master.supplier.update",
        ],
    },
    "po": {
        "display_name": "采购",
        "perms": [
            "workbench",
            "master.supplier.list", "master.supplier.create", "master.supplier.update", "master.supplier.export",
            "master.spec.list", "master.spec.create", "master.spec.update",
            "master.spec.price_write", "master.spec.import", "master.spec.export",
        ],
    },
    "op": {
        "display_name": "运营",
        "perms": [
            "workbench",
            "master.spec.list", "master.spec.export",
            "master.shop_product.list", "master.shop_product.create",
            "master.shop_product.update", "master.shop_product.export",
            "roi.list", "roi.create",
        ],
    },
    "fin": {
        "display_name": "财务",
        "perms": [
            "workbench",
            "master.spec.list", "master.spec.export",
            "calc.list", "calc.upload", "calc.export",
            "calc.manual_match", "calc.recalc", "calc.ignore",
            "report.list", "report.export",
        ],
    },
}


def expand_admin(perms: list[str]) -> list[str]:
    if "*" in perms:
        # 管理员在 current_user.perms 里仍用 ["*"]，鉴权层放行
        return perms
    return perms
