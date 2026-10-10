"""Tests for the Price stage (plans/10-price.md). Inputs are built by hand; no network."""

import math
import re
from datetime import date

import pytest

from rfq.context import Context
from rfq.models import Candidate, Line, Offer, Segment, Spec, Terms
from rfq.price import piece_weight_lb, price
from rfq.reference import load_reference

REF = load_reference()
CTX = Context(terms=Terms(), ref=REF, today=date(2026, 10, 10))

SHEET = "SS-304L-SHT-0625-48X96"
BELOW_FLOOR = "SS-316L-PLT-2500-48X96"
ROUND_BAR = "CS-1018-RB-1000-144"


def make_line(sku: str, qty: float, unit: str, label: str = "As requested", **dims) -> Line:
    offer = Offer(label=label, spec=Spec(quantity=qty, quantity_unit=unit, **dims),
                  candidate=Candidate(sku=sku, description="x", strength=1.0))
    return Line(buyer_line_no="1", segment=Segment(buyer_line_no="1", text="x"), offers=[offer])


def priced(sku, qty, unit, **dims):
    line = price(make_line(sku, qty, unit, **dims), CTX)
    return line, line.offers[0].price


def test_each_reproduces_by_hand():
    line, p = priced(SHEET, 10, "ea", thickness_in=0.0625, width_in=48, length_in=96)
    per_lb = round(2.10 * 0.97, 4)
    piece = 0.0625 * 48 * 96 * 0.289
    assert p.unit == "ea"
    assert p.unit_price == round(per_lb * piece, 2)
    assert p.extended == round(p.unit_price * 10, 2)
    assert p.weight_lb == round(piece * 10, 2)
    assert p.numbers["price_per_lb"] == 2.037
    assert p.position == "below_mid"
    assert p.valid_until == "2026-10-17"
    assert [c.name for c in p.components] == ["base"]
    assert p.components[0].amount == p.extended
    assert p.cost_per_lb == 1.72
    assert p.margin_pct == round((2.037 - 1.72) / 2.037 * 100, 1)
    assert line.issues == []


def test_pounds_priced_per_lb():
    _, p = priced(SHEET, 500, "lb")
    assert p.unit == "lb" and p.unit_price == 2.037
    assert p.extended == round(2.037 * 500, 2)
    assert p.weight_lb == 500


def test_cwt():
    _, p = priced(SHEET, 3, "cwt")
    assert p.unit == "cwt" and p.unit_price == 203.7
    assert p.extended == round(203.7 * 3, 2)
    assert p.weight_lb == 300


def test_feet_uses_item_length_fallback():
    # 1 in carbon round bar, ordered by the foot, no length in the spec
    _, p = priced(ROUND_BAR, 50, "ft", diameter_in=1.0)
    per_ft = math.pi / 4 * 1.0**2 * 12 * REF.tables.density_lb_per_in3["carbon"]
    per_lb = round(0.90 * 0.97, 4)
    assert p.unit == "ft"
    assert p.unit_price == round(per_lb * per_ft, 2)
    assert p.extended == round(p.unit_price * 50, 2)
    assert p.weight_lb == pytest.approx(per_ft * 50, abs=0.01)


def test_piece_weight_forms():
    d = REF.tables.density_lb_per_in3
    cases = [
        ("SS-304L-FB-2500X2000-144", Spec(), 0.25 * 2 * 144 * d["stainless"]),
        ("SS-304L-RT-1000X065-240", Spec(),
         math.pi / 4 * (1 - 0.87**2) * 240 * d["stainless"]),
        ("CS-A500-ST-2000X120-240", Spec(), (4 - 1.76**2) * 240 * d["carbon"]),
        (ROUND_BAR, Spec(length_in=24), math.pi / 4 * 24 * d["carbon"]),
    ]
    for sku, spec, expected in cases:
        assert piece_weight_lb(spec, REF.item(sku), CTX) == pytest.approx(expected)


def test_piece_weight_prefers_spec_dimensions():
    item = REF.item(SHEET)
    w = piece_weight_lb(Spec(length_in=48), item, CTX)
    assert w == pytest.approx(0.0625 * 48 * 48 * 0.289)


def test_piece_weight_missing_dimension_raises():
    item = REF.item(SHEET).model_copy(update={"thickness_in": None})
    with pytest.raises(ValueError):
        piece_weight_lb(Spec(), item, CTX)


def test_below_floor_keeps_price_and_flags_line():
    line, p = priced(BELOW_FLOOR, 2, "ea", thickness_in=0.25, width_in=48, length_in=96)
    assert p is not None and p.margin_pct == 5.3 and p.floor_margin_pct == 12.0
    assert p.unit_price == round(round(2.95 * 0.97, 4) * 0.25 * 48 * 96 * 0.289, 2)
    kinds = [(i.kind, i.audience) for i in line.issues]
    assert kinds == [("below_floor", "internal")]
    assert "5.3%" in line.issues[0].message and "12.0%" in line.issues[0].message


def test_no_benchmark_leaves_price_none():
    ref = REF.model_copy(update={"benchmarks": {}})
    ctx = Context(terms=Terms(), ref=ref, today=CTX.today)
    line = price(make_line(SHEET, 1, "ea"), ctx)
    assert line.offers[0].price is None
    assert [(i.kind, i.audience) for i in line.issues] == [("unconfirmed", "internal")]


def test_skips_when_nothing_to_price():
    empty = Line(buyer_line_no="1", segment=Segment(buyer_line_no="1", text="x"))
    assert price(empty, CTX) is empty and empty.offers == []
    no_cand = make_line(SHEET, 1, "ea")
    no_cand.offers[0].candidate = None
    no_qty = make_line(SHEET, 1, "ea")
    no_qty.offers[0].spec.quantity = None
    for line in (no_cand, no_qty):
        price(line, CTX)
        assert line.offers[0].price is None and line.issues == []


def test_each_offer_priced_and_issues_name_the_offer():
    line = make_line(SHEET, 1, "ea", label="Option A")
    line.offers.append(make_line(BELOW_FLOOR, 1, "ea", label="Option B").offers[0])
    price(line, CTX)
    assert all(o.price for o in line.offers)
    assert len(line.issues) == 1 and line.issues[0].message.startswith("Option B: ")


def test_rationale_buyer_safe_and_numbers_match():
    _, p = priced(BELOW_FLOOR, 2, "ea", thickness_in=0.25, width_in=48, length_in=96)
    text = p.rationale
    assert "synthetic" in text and "2026-10-01" in text
    for word in ("cost", "margin", "floor", "supplier"):
        assert word not in text.lower()
    figures = [float(x) for x in re.findall(r"\d+\.\d+", re.sub(r"\d{4}-\d{2}-\d{2}", "", text))]
    assert figures
    for f in figures:
        assert any(f == v for v in p.numbers.values()), f
    # each number's formatting reproduces from numbers
    n = p.numbers
    assert f"${n['price_per_lb']:.4f}/lb" in text
    assert f"{n['pct_below_mid']:.1f}%" in text
    assert f"${n['benchmark_low']:.2f}-${n['benchmark_high']:.2f}/lb" in text


def test_position_within_and_above_range():
    for mult, position in ((1.02, "within_range"), (1.20, "above_range")):
        rules = REF.rules.pricing.model_copy(update={"target_multiplier_of_benchmark_mid": mult})
        ref = REF.model_copy(update={"rules": REF.rules.model_copy(update={"pricing": rules})})
        ctx = Context(terms=Terms(), ref=ref, today=CTX.today)
        p = price(make_line(SHEET, 1, "ea"), ctx).offers[0].price
        assert p.position == position
        assert "synthetic" in p.rationale
        for f in re.findall(r"\d+\.\d+", re.sub(r"\d{4}-\d{2}-\d{2}", "", p.rationale)):
            assert float(f) in p.numbers.values()
