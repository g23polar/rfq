"""The rule stages wired together (tasks 08 to 12), on golden-set lines with hand-built readings.

The interpretation stage (task 06) is not part of this: each Reading below is what it should
produce for the line.
"""
import json
from datetime import date
from pathlib import Path

import pytest

from rfq import availability, compliance, decide, match, price, standardize, verify
from rfq.context import Context
from rfq.models import Line, Reading, Segment, Sourced, Terms, buyer_view, Run, RunSource
from rfq.reference import load_reference

GOLDEN = {g["id"]: g for g in map(json.loads, (Path(__file__).parent.parent / "fixtures"
                                               / "golden.jsonl").read_text().splitlines())}


def s(value, unit=None, text=None):
    return Sourced(value=value, unit=unit, source_text=text or str(value))


def dims(*values):
    return [s(v) for v in values]


READINGS = {
    "email-1": Reading(grade=s("304"), material=s("SS"), form=s("sheet"), gauge=s("16", "ga"),
                       unlabeled_dimensions=dims("4", "8"), quantity=s("10", "ea")),
    "email-2": Reading(grade=s("304"), material=s("Stainless"), thickness=s("0.060", "in"),
                       unlabeled_dimensions=dims("48", "96"), quantity=s("6", "ea")),
    "email-3": Reading(material=s("Stainless"), form=s("sheet"), gauge=s("16", "ga"),
                       unlabeled_dimensions=dims("4", "8"), quantity=s("12", "ea")),
    "email-4": Reading(customer_part_no=s("ACME-PN 88213"), quantity=s("20", "ea")),
    "email-5": Reading(grade=s("316"), material=s("SS"), form=s("round bar"),
                       diameter=s("1-1/2", '"'), length=s("12", "ft"), quantity=s("4", "ea")),
    "email-6": Reading(grade=s("316"), material=s("SS"), form=s("plate"), thickness=s("1/4"),
                       unlabeled_dimensions=dims("48", "96"), quantity=s("2", "ea")),
    "pdf-1": Reading(grade=s("304"), material=s("stainless"), form=s("sheet"),
                     gauge=s("16", "ga"), thickness=s("0.075", "in"),
                     unlabeled_dimensions=dims("48", "96"), quantity=s("15", "ea")),
    "pdf-3": Reading(grade=s("1018"), material=s("CRS"), form=s("round bar"),
                     diameter=s("1", "in"), length=s("12", "ft"), quantity=s("1,500", "lb")),
    "pdf-6": Reading(grade=s("Inconel 625"), form=s("plate"), thickness=s("3/8"),
                     unlabeled_dimensions=dims("48", "96"), quantity=s("3", "ea")),
    "pdf-7": Reading(grade=s("A36"), form=s("plate"), thickness=s("1/4", "in"),
                     width=s("48", "in"), length=s("96", "in"), standard=s("ASTM A36"),
                     quantity=s("10", "ea")),
    "pdf-8": Reading(grade=s("304"), material=s("SS"), form=s("sheet"), gauge=s("11", "ga"),
                     unlabeled_dimensions=dims("48", "120"), quantity=s("12", "ea")),
    "std-8": Reading(grade=s("316"), material=s("SS"), form=s("round bar"),
                     diameter=s("1-1/2", "in"), length=s("144", "in"), quantity=s("2", "ea"),
                     requirements=[s("DFARS not required", text="DFARS not required for this line")]),
    "std-9": Reading(grade=s("A36"), form=s("plate"), thickness=s("3/8", "in"),
                     width=s("48", "in"), length=s("96", "in"), standard=s("ASTM A36"),
                     quantity=s("4", "ea")),
    "std-11": Reading(grade=s("304"), material=s("SS"), form=s("sheet"), gauge=s("18", "ga"),
                      width=s("48", "in"), length=s("96", "in"), quantity=s("8", "ea")),
    "std-13": Reading(grade=s("1018"), form=s("rd bar"), diameter=s("1"), length=s("12"),
                      quantity=s("10", "ea")),
}


def run_line(golden_id: str) -> Line:
    g = GOLDEN[golden_id]
    terms = Terms(
        customer=Sourced(value=g["customer"], source="rfq_terms") if g.get("customer") else None,
        requirements=[Sourced(value=r, source_text=r, source="rfq_terms")
                      for r in g.get("rfq_requirements", [])])
    ctx = Context(terms=terms, ref=load_reference(), today=date(2026, 10, 10))
    no = g.get("buyer_line_no") or "1"
    line = Line(buyer_line_no=no,
                segment=Segment(buyer_line_no=no, text=g["text"]),
                reading=READINGS[golden_id])
    for stage in (standardize.standardize, match.resolve, availability.check, price.price,
                  compliance.check, decide.decide, verify.verify):
        line = stage(line, ctx)
    return line


@pytest.mark.parametrize("golden_id", sorted(READINGS))
def test_golden_line_reaches_expected_status_and_item(golden_id):
    expected = GOLDEN[golden_id]["expected"]
    line = run_line(golden_id)
    detail = [(i.kind, i.field, i.message) for i in line.issues]
    assert line.status == expected["status"], detail
    if expected.get("skus"):
        assert sorted(o.candidate.sku for o in line.offers) == sorted(expected["skus"]), detail
    if line.verification:
        assert line.verification.passed or line.status == "needs_specialist_review", \
            line.verification.failures


def test_short_stock_is_quoted_with_the_shortfall_stated():
    """Golden pdf-4 asks for 8 of an item with 3 in stock: still quoted, partial (Q4)."""
    READINGS["pdf-4"] = Reading(grade=s("304"), material=s("SS"), form=s("plate"),
                                thickness=s("1/4", "in"), width=s("48", "in"),
                                length=s("96", "in"), standard=s("ASTM A240"),
                                quantity=s("8", "ea"))
    line = run_line("pdf-4")
    del READINGS["pdf-4"]
    assert line.status == GOLDEN["pdf-4"]["expected"]["status"]
    a = line.offers[0].availability
    assert (a.status, a.available_qty, a.shortfall_qty) == ("partial", 3, 5)


def test_track_strings_share_a_fingerprint():
    assert run_line("email-1").spec.fingerprint == run_line("email-2").spec.fingerprint


def test_chain_output_has_no_internal_data_for_the_buyer():
    lines = [run_line(i) for i in sorted(READINGS)]
    run = Run(rfq_id="Q-CHAIN", created="2026-10-10T12:00:00-04:00",
              source=RunSource(kind="text"), lines=lines)
    for n, line in enumerate(lines):
        line.buyer_line_no = line.segment.buyer_line_no = str(n + 1)
    held = {l.buyer_line_no for l in lines if l.status == "needs_specialist_review"}
    quote = buyer_view(run)
    assert held and not held & {l.buyer_line_no for l in quote.lines}
    check = verify.leak_check(run, [quote.model_dump_json()])
    assert check.passed, check.hits
