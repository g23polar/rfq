import math
from datetime import date

import pytest

from rfq import availability
from rfq.context import Context
from rfq.models import Candidate, Line, Offer, Segment, Spec, Terms
from rfq.reference import load_reference

REF = load_reference()
CTX = Context(terms=Terms(), ref=REF, today=date(2026, 10, 10))
PLATE = "SS-304L-PLT-2500-48X96"  # seeded: 3 in stock, 21 day lead time
BAR = "CS-1018-RB-1000-144"


def offer(sku, qty, unit="ea", label="As requested", **spec):
    item = REF.item(sku)
    return Offer(label=label, candidate=Candidate(sku=sku, description=item.description, strength=1),
                 spec=Spec(quantity=qty, quantity_unit=unit, **spec))


def check(*offers):
    line = Line(buyer_line_no="1", segment=Segment(buyer_line_no="1", text="x"), offers=list(offers))
    before = list(line.issues), line.status
    line = availability.check(line, CTX)
    assert (list(line.issues), line.status) == before  # availability never changes these
    return [o.availability for o in line.offers]


def test_quantity_above_stock_is_partial_with_the_shortfall():
    (a,) = check(offer(PLATE, 8))
    assert (a.status, a.available_qty, a.shortfall_qty, a.lead_time_days) == ("partial", 3, 5, 21)


def test_quantity_within_stock_is_in_stock_with_no_lead_time():
    (a,) = check(offer(PLATE, 3))
    assert (a.status, a.available_qty, a.shortfall_qty, a.lead_time_days) == ("in_stock", 3, 0, None)


def test_no_stock_is_not_stocked_and_promises_nothing_but_lead_time(monkeypatch):
    item = REF.item(PLATE)
    monkeypatch.setattr(item, "stock_qty", 0)
    (a,) = check(offer(PLATE, 2))
    assert (a.status, a.available_qty, a.shortfall_qty) == ("not_stocked", 0, 2)
    assert a.lead_time_days == item.lead_time_days


def test_pounds_are_converted_with_the_pricing_weight():
    item = REF.item(BAR)
    piece = math.pi / 4 * 1.0**2 * 144 * REF.tables.density_lb_per_in3["carbon"]
    on_hand = item.stock_qty * piece
    (within,) = check(offer(BAR, round(on_hand - 10), "lb"))
    (over,) = check(offer(BAR, round(on_hand + 500), "lb"))
    assert within.status == "in_stock"
    assert over.status == "partial"
    assert over.available_qty == pytest.approx(on_hand, abs=0.01)
    assert over.shortfall_qty == pytest.approx(round(on_hand + 500) - on_hand, abs=0.01)
    (cwt,) = check(offer(BAR, round(on_hand / 100) + 5, "cwt"))
    assert cwt.status == "partial" and cwt.available_qty == pytest.approx(on_hand / 100, abs=0.01)


def test_feet_are_converted_from_stock_lengths():
    item = REF.item(BAR)
    feet = item.stock_qty * item.length_in / 12
    (a,) = check(offer(BAR, feet + 24, "ft"))
    assert (a.status, a.available_qty, a.shortfall_qty) == ("partial", feet, 24)


def test_each_alternate_gets_its_own_availability():
    a, b = check(offer(PLATE, 8, label="Option A"), offer("SS-316L-PLT-2500-48X96", 1, label="Option B"))
    assert a.status == "partial" and b.status == "in_stock"


def test_offers_without_a_candidate_or_quantity_are_left_alone():
    no_qty = Offer(label="x", spec=Spec(), candidate=Candidate(sku=PLATE, description="d", strength=1))
    assert check(Offer(label="x", spec=Spec(quantity=1, quantity_unit="ea")), no_qty) == [None, None]
