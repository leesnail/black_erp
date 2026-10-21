# -*- coding: utf-8 -*-
"""匹配引擎：纯函数，可单测可复算（FR-LINK-01）"""
from dataclasses import dataclass
from decimal import Decimal

from app.common.csv_parser import RawOrder, normalize_title, split_product


@dataclass
class Candidate:
    sp_id: int
    shop_id: int
    title_keyword: str
    title_norm: str
    spec_name: str
    sale_price: Decimal
    spec_id: int


@dataclass
class MatchRuleRow:
    shop_id: int
    title_norm: str
    spec_text: str
    spec_id: int


@dataclass
class Scored:
    cand: Candidate | None
    prio: int  # 0 最高
    tie: int   # 越小越好（命中长度取负）
    spec_id: int | None = None

    @property
    def auto_ok(self) -> bool:
        return self.cand is not None and self.prio <= 2


PRICE_TOL = Decimal("0.01")


def score_candidate(
    cand: Candidate,
    title_norm: str,
    spec_text: str,
    unit_price: Decimal | None,
    rules: dict[tuple[str, str], int],
) -> tuple[int, int]:
    """返回 (prio, tie) 越小越优"""
    # P0 MatchRule 精确
    if (title_norm, spec_text) in rules or title_norm in {k[0] for k in rules}:
        # 简化：title_norm 命中规则即 P0
        for (tn, _st), _sid in rules.items():
            if tn == title_norm:
                return (0, 0)

    hit_len = 0
    kw = cand.title_norm
    if kw and (kw in title_norm or title_norm in kw):
        hit_len = min(len(kw), len(title_norm))

    price_eq = (
        unit_price is not None
        and abs(unit_price - cand.sale_price) <= PRICE_TOL
    )
    spec_eq = spec_text and cand.spec_name and normalize_title(spec_text) == normalize_title(cand.spec_name)

    if spec_eq and price_eq:
        return (1, 0)
    if hit_len > 0 and price_eq:
        return (2, -hit_len)
    if hit_len > 0:
        return (3, -hit_len)
    return (9, 0)


def match_order(
    order: RawOrder,
    candidates: list[Candidate],
    rules: dict[tuple[str, str], int],
) -> Scored:
    """对单行订单做匹配；返回最优 Scored"""
    title, spec_text = split_product(order.raw_product)
    title_norm = normalize_title(title)
    unit_price = (order.income / order.qty).quantize(Decimal("0.01")) if order.qty else None

    if not candidates:
        return Scored(cand=None, prio=9, tie=0)

    scored: list[Scored] = []
    for cand in candidates:
        # 规则优先：规则表里有该 title_norm 直接给 P0 并绑定规则 spec
        rule_spec = None
        for (tn, st), sid in rules.items():
            if tn == title_norm and (st == spec_text or st == ""):
                rule_spec = sid
                break
        if rule_spec is not None:
            scored.append(Scored(cand=cand, prio=0, tie=0, spec_id=rule_spec))
            continue
        prio, tie = score_candidate(cand, title_norm, spec_text, unit_price, rules)
        scored.append(Scored(cand=cand, prio=prio, tie=tie, spec_id=cand.spec_id))

    scored.sort(key=lambda s: (s.prio, s.tie))
    best = scored[0]

    # 并列最高优先级 → 不自动
    same_top = [s for s in scored if s.prio == best.prio and s.tie == best.tie]
    if len(same_top) > 1 and best.prio < 9:
        return Scored(cand=best.cand, prio=best.prio, tie=best.tie, spec_id=None)

    return best


def top_candidates(
    order: RawOrder,
    candidates: list[Candidate],
    rules: dict[tuple[str, str], int],
    n: int = 3,
) -> list[Scored]:
    title, spec_text = split_product(order.raw_product)
    title_norm = normalize_title(title)
    unit_price = (order.income / order.qty).quantize(Decimal("0.01")) if order.qty else None
    scored = []
    for cand in candidates:
        prio, tie = score_candidate(cand, title_norm, spec_text, unit_price, rules)
        scored.append(Scored(cand=cand, prio=prio, tie=tie, spec_id=cand.spec_id))
    scored.sort(key=lambda s: (s.prio, s.tie))
    return scored[:n]


def build_recall_index(candidates: list[Candidate]) -> list[Candidate]:
    """倒排可选；当前规模直接返回（预热已加载本店启用登记）"""
    return candidates
