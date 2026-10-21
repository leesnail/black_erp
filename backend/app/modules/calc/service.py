# -*- coding: utf-8 -*-
"""核算核心服务：加载上下文、处理单行、汇总、批量落库"""
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.csv_parser import RawOrder, normalize_title, split_product
from app.modules.calc import models as cm
from app.modules.calc.matcher import Candidate, MatchRuleRow, Scored, match_order, top_candidates
from app.modules.master import models as mm

ZERO = Decimal("0.01")
SURCHARGE_DEFAULT = Decimal("0")


@dataclass
class CalcContext:
    shop_id: int
    candidates: list[Candidate] = field(default_factory=list)
    rules: dict[tuple[str, str], int] = field(default_factory=dict)
    region_rules: list[tuple[set[str], Decimal]] = field(default_factory=list)
    price_map: dict[int, Decimal] = field(default_factory=dict)  # spec_id -> 当前有效价

    def region_surcharge(self, province: str) -> Decimal:
        if not province:
            return SURCHARGE_DEFAULT
        p = province.strip()
        for provinces, amount in self.region_rules:
            for key in provinces:
                if key and (key in p or p in key):
                    return amount
        return SURCHARGE_DEFAULT


async def load_context(db: AsyncSession, shop_id: int) -> CalcContext:
    ctx = CalcContext(shop_id=shop_id)

    # 启用登记 + join spec
    rows = await db.execute(
        select(mm.ShopProduct, mm.Spec)
        .join(mm.Spec, mm.ShopProduct.spec_id == mm.Spec.id)
        .where(mm.ShopProduct.shop_id == shop_id, mm.ShopProduct.status == "active")
    )
    sp_list: list[tuple[mm.ShopProduct, mm.Spec]] = list(rows.all())

    spec_ids = [sp.spec_id for sp, _ in sp_list]
    # 当前价（每 spec 最新 effective_at）
    if spec_ids:
        from sqlalchemy import func

        sub = (
            select(mm.CostPrice.spec_id, func.max(mm.CostPrice.effective_at).label("mx"))
            .where(mm.CostPrice.spec_id.in_(spec_ids))
            .group_by(mm.CostPrice.spec_id)
            .subquery()
        )
        price_rows = await db.execute(
            select(mm.CostPrice.spec_id, mm.CostPrice.price).join(
                sub,
                (mm.CostPrice.spec_id == sub.c.spec_id)
                & (mm.CostPrice.effective_at == sub.c.mx),
            )
        )
        ctx.price_map = dict(price_rows.all())

    for sp, spec in sp_list:
        ctx.candidates.append(
            Candidate(
                sp_id=sp.id,
                shop_id=sp.shop_id,
                title_keyword=sp.title_keyword,
                title_norm=normalize_title(sp.title_keyword),
                spec_name=spec.spec_name,
                sale_price=sp.sale_price,
                spec_id=spec.id,
            )
        )

    # MatchRule
    rule_rows = (
        await db.scalars(select(cm.MatchRule).where(cm.MatchRule.shop_id == shop_id))
    ).all()
    for r in rule_rows:
        ctx.rules[(r.title_norm, r.spec_text or "")] = r.spec_id

    # RegionRule
    region_rows = (
        await db.scalars(select(mm.RegionRule).where(mm.RegionRule.status == "active"))
    ).all()
    for r in region_rows:
        provinces = set(r.provinces or [])
        ctx.region_rules.append((provinces, r.amount))

    return ctx


def candidates_for_title(ctx: CalcContext, title_norm: str) -> list[Candidate]:
    """倒排召回：互为子串"""
    out = []
    for c in ctx.candidates:
        kw = c.title_norm
        if kw and (kw in title_norm or title_norm in kw):
            out.append(c)
    return out


@dataclass
class LineResult:
    order_no: str
    raw_product: str
    title: str
    spec_text: str
    qty: int
    province: str
    spec_id: int | None
    price_snapshot: Decimal | None
    surcharge: Decimal
    unit_cost: Decimal | None
    line_cost: Decimal | None
    income: Decimal
    matched: str  # auto|manual|none
    aftersale_status: str


def process_line(raw: RawOrder, ctx: CalcContext) -> LineResult:
    title, spec_text = split_product(raw.raw_product)
    title_norm = normalize_title(title)
    cands = candidates_for_title(ctx, title_norm)
    best: Scored = match_order(raw, cands, ctx.rules)

    matched = "none"
    spec_id: int | None = None
    price: Decimal | None = None

    if best.auto_ok and best.spec_id is not None:
        matched = "auto"
        spec_id = best.spec_id
        price = ctx.price_map.get(spec_id)

    surcharge = ctx.region_surcharge(raw.province)
    unit_cost = (price + surcharge) if price is not None else None
    line_cost = (unit_cost * raw.qty).quantize(ZERO) if unit_cost is not None else None

    return LineResult(
        order_no=raw.order_no,
        raw_product=raw.raw_product,
        title=title,
        spec_text=spec_text,
        qty=raw.qty,
        province=raw.province,
        spec_id=spec_id,
        price_snapshot=price,
        surcharge=surcharge,
        unit_cost=unit_cost,
        line_cost=line_cost,
        income=raw.income,
        matched=matched,
        aftersale_status=raw.aftersale_status,
    )


def aggregate(lines: list[LineResult]) -> dict:
    income_total = sum((ln.income for ln in lines), Decimal("0")).quantize(ZERO)
    cost_total = sum(
        (ln.line_cost for ln in lines if ln.line_cost is not None and ln.matched != "none"),
        Decimal("0"),
    ).quantize(ZERO)
    ship_count = len(lines)
    aftersale = sum(1 for ln in lines if ln.aftersale_status)
    unmatched = sum(1 for ln in lines if ln.matched == "none")
    auto = sum(1 for ln in lines if ln.matched == "auto")
    profit = (income_total - cost_total).quantize(ZERO)
    return {
        "total": ship_count,
        "ship_count": ship_count,
        "aftersale": aftersale,
        "matched_auto": auto,
        "matched_manual": 0,
        "unmatched": unmatched,
        "income_total": str(income_total),
        "cost_total": str(cost_total),
        "profit": str(profit),
    }


async def bulk_insert_lines(db: AsyncSession, batch_id: int, results: list[LineResult]) -> None:
    objs = [
        cm.OrderLine(
            batch_id=batch_id,
            order_no=r.order_no,
            raw_product=r.raw_product,
            title=r.title,
            spec_text=r.spec_text,
            qty=r.qty,
            province=r.province,
            spec_id=r.spec_id,
            price_snapshot=r.price_snapshot,
            surcharge=r.surcharge,
            unit_cost=r.unit_cost,
            line_cost=r.line_cost,
            income=r.income,
            matched=r.matched,
            aftersale_status=r.aftersale_status or None,
        )
        for r in results
    ]
    db.add_all(objs)
    await db.flush()


async def recommendations_for_line(db: AsyncSession, line: cm.OrderLine, ctx: CalcContext, n: int = 3):
    from app.common.csv_parser import RawOrder

    raw = RawOrder(
        order_no=line.order_no,
        raw_product=line.raw_product,
        express="x",
        province=line.province or "",
        qty=line.qty,
        income=line.income,
        aftersale_status=line.aftersale_status or "",
    )
    title, _ = split_product(line.raw_product)
    cands = candidates_for_title(ctx, normalize_title(title))
    tops = top_candidates(raw, cands, ctx.rules, n=n)
    out = []
    for t in tops:
        if t.cand:
            out.append(
                {
                    "spec_id": t.cand.spec_id,
                    "spec_code": await _spec_code(db, t.cand.spec_id),
                    "product_name": t.cand.title_keyword,
                    "prio": t.prio,
                }
            )
    return out


async def _spec_code(db: AsyncSession, spec_id: int) -> str:
    spec = await db.get(mm.Spec, spec_id)
    return spec.spec_code if spec else ""
