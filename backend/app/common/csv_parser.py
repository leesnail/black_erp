# -*- coding: utf-8 -*-
"""CSV 解析与预检（关键列配置化）"""
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any, Iterator

import pandas as pd

# 抖店订单导出关键列（可配置适配改版）
COLUMN_MAP = {
    "选购商品": ["选购商品", "商品名称"],
    "快递信息": ["快递信息", "物流单号"],
    "省": ["省", "省份", "收货省份"],
    "商品数量": ["商品数量", "数量"],
    "商家收入金额": ["商家收入金额", "商家收入"],
    "售后状态": ["售后状态"],
    "子订单编号": ["子订单编号", "订单编号"],
}


@dataclass
class RawOrder:
    order_no: str
    raw_product: str
    express: str
    province: str
    qty: int
    income: Decimal
    aftersale_status: str


@dataclass
class ParseResult:
    total: int = 0
    no_ship: int = 0
    aftersale: int = 0
    qty_invalid: int = 0
    rows: list[RawOrder] = field(default_factory=list)
    errors: list[dict] = field(default_factory=list)
    shop_guess: str = ""


def guess_shop(filename: str) -> str:
    """文件名前 2 字 = 店铺名"""
    stem = filename.rsplit(".", 1)[0]
    return stem[:2].strip()


def _resolve_columns(df: pd.DataFrame) -> dict[str, str]:
    """返回 canonical -> actual 列名"""
    actual = {str(c).strip(): str(c) for c in df.columns}
    resolved: dict[str, str] = {}
    missing: list[str] = []
    for canon, candidates in COLUMN_MAP.items():
        found = None
        for cand in candidates:
            if cand in actual:
                found = actual[cand]
                break
        if found:
            resolved[canon] = found
        else:
            missing.append(canon)
    if missing:
        raise ValueError(f"CSV 缺少关键列: {missing}；实际列: {list(actual)}")
    return resolved


def _is_no_ship(v: Any) -> bool:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return True
    s = str(v).strip()
    return s == "" or s == "-" or s.lower() == "nan"


def _to_int(v: Any) -> int | None:
    try:
        n = int(float(v))
        return n if n > 0 else None
    except (TypeError, ValueError):
        return None


def _to_dec(v: Any) -> Decimal:
    try:
        return Decimal(str(v)).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0")


def iter_orders(file_path: str, chunksize: int = 5000) -> Iterator[pd.DataFrame]:
    for chunk in pd.read_csv(file_path, encoding="utf-8-sig", chunksize=chunksize, dtype=str):
        yield chunk


def parse_chunk(chunk: pd.DataFrame) -> ParseResult:
    cols = _resolve_columns(chunk)
    result = ParseResult(total=len(chunk))

    for idx, row in chunk.iterrows():
        express = row[cols["快递信息"]]
        product = str(row[cols["选购商品"]] or "").strip()
        if not product:
            result.errors.append({"row": int(idx) + 2, "reason": "选购商品为空"})
            continue

        if _is_no_ship(express):
            result.no_ship += 1
            continue

        qty = _to_int(row[cols["商品数量"]])
        if qty is None:
            result.qty_invalid += 1
            result.errors.append({"row": int(idx) + 2, "reason": "商品数量无效: {}".format(row[cols["商品数量"]])})
            continue

        income = _to_dec(row[cols["商家收入金额"]])
        aftersale = str(row.get(cols["售后状态"], "") or "").strip()
        if aftersale and aftersale.lower() != "nan":
            result.aftersale += 1

        result.rows.append(
            RawOrder(
                order_no=str(row[cols["子订单编号"]] or "").strip(),
                raw_product=product,
                express=str(express).strip(),
                province=str(row.get(cols["省"], "") or "").strip(),
                qty=qty,
                income=income,
                aftersale_status=aftersale if aftersale.lower() != "nan" else "",
            )
        )
    return result


def split_product(raw: str) -> tuple[str, str]:
    """按最后一个 '-' 拆分标题与规格"""
    if "-" in raw:
        i = raw.rfind("-")
        return raw[:i].strip(), raw[i + 1 :].strip()
    return raw.strip(), ""


def normalize_title(title: str) -> str:
    """去空白、全半角统一、去装饰符"""
    import re
    import unicodedata

    t = unicodedata.normalize("NFKC", title)
    t = re.sub(r"[\s【】\[\]（）()【】\*＊·、，,。.]", "", t)
    return t.lower()
