"""Tests for stage 5, resolve to catalog (plans/09-match.md). Specs are built by hand."""

import json
from datetime import date
from pathlib import Path

import pytest

from rfq.context import Context
from rfq.match import resolve
from rfq.models import Line, Reading, Segment, Sourced, Spec, Terms, issue
from rfq.reference import load_reference

GOLDEN = Path(__file__).parent.parent / "fixtures" / "golden.jsonl"
SHEET_16GA = dict(material="stainless", form="sheet", thickness_in=0.0625, width_in=48,
                  length_in=96, quantity=10, quantity_unit="ea")


def ctx(customer="Acme Fabrication") -> Context:
    terms = Terms(customer=Sourced(value=customer) if customer else None)
    return Context(terms=terms, ref=load_reference(), today=date(2026, 10, 10))


def make(spec=None, issues=(), part_no=None, kind="item", grade_text=None) -> Line:
    reading = Reading(customer_part_no=Sourced(value=part_no) if part_no else None,
                      grade=Sourced(value=grade_text) if grade_text else None)
    return Line(buyer_line_no="1", segment=Segment(buyer_line_no="1", text="x", kind=kind),
                reading=reading, spec=Spec(**spec) if spec is not None else None,
                issues=list(issues))


def kinds(line):
    return [i.kind for i in line.issues]


def test_not_an_item_or_no_spec_is_untouched():
    assert resolve(make(SHEET_16GA | {"grade": "304"}, kind="requirement"), ctx()).offers == []
    line = resolve(make(None), ctx())
    assert line.offers == [] and line.issues == []


@pytest.mark.parametrize("grade", ["304", "304L"])
def test_dual_certified_fills_plain_request(grade):
    line = resolve(make(SHEET_16GA | {"grade": grade}), ctx())
    assert [o.candidate.sku for o in line.offers] == ["SS-304L-SHT-0625-48X96"]
    assert line.offers[0].label == "As requested"
    assert line.offers[0].candidate.strength == 1.0
    assert line.offers[0].spec.standard == "ASTM A240"
    assert kinds(line) == ["assumption"]


def test_304h_and_straight_only_are_not_filled_by_dual_stock():
    for grade, text in (("304H", None), ("304", "304 straight grade only")):
        line = resolve(make(SHEET_16GA | {"grade": grade}, grade_text=text), ctx())
        assert not any(o.label == "As requested" for o in line.offers)
        assert "assumption" not in kinds(line)


def test_304h_request_is_a_no_bid_not_a_substitute():
    """Dual-certified stock cannot fill 304H, and low-carbon 316/316L is no substitute for it."""
    line = resolve(make(SHEET_16GA | {"grade": "304H"}), ctx())
    assert line.offers == []
    assert kinds(line) == ["no_match"]
    assert line.issues[0].audience == "buyer"


def test_exact_single_grade_item_has_no_issues():
    spec = dict(material="carbon", grade="A36", form="plate", thickness_in=0.25, width_in=48,
                length_in=96, standard="ASTM A36")
    line = resolve(make(spec), ctx())
    assert [o.candidate.sku for o in line.offers] == ["CS-A36-PLT-2500-48X96"]
    assert line.issues == []


def test_thickness_within_tolerance_matches_with_assumption():
    spec = dict(material="aluminum", grade="5052-H32", form="sheet", thickness_in=0.0508,
                width_in=48, length_in=96)
    line = resolve(make(spec), ctx())
    assert line.offers[0].candidate.sku == "AL-5052H32-SHT-0500-48X96"
    assert 0.8 <= line.offers[0].candidate.strength < 1.0
    assert line.offers[0].candidate.differences
    assert kinds(line) == ["assumption"]


def test_missing_grade_alternates_for_each_option():
    amb = issue("ambiguous_options", "Which grade?", "grade", ["304", "316"])
    line = resolve(make(SHEET_16GA, [amb]), ctx())
    assert [(o.label, o.candidate.sku) for o in line.offers] == [
        ("Option A: 304/304L", "SS-304L-SHT-0625-48X96"),
        ("Option B: 316/316L", "SS-316L-SHT-0625-48X96")]
    assert [o.spec.grade for o in line.offers] == ["304", "316"]
    assert all(o.spec.standard == "ASTM A240" for o in line.offers)
    assert kinds(line) == ["ambiguous_options"]


def test_options_with_no_limit_and_unmatched_option_dropped():
    spec = dict(material="carbon", form="round_bar", diameter_in=1.0, length_in=144)
    amb = issue("ambiguous_options", "Which grade?", "grade", ["1018", "1045", "A36"])
    line = resolve(make(spec, [amb]), ctx())
    assert [o.candidate.sku for o in line.offers] == ["CS-1018-RB-1000-144",
                                                      "CS-1045-RB-1000-144"]


def test_options_filled_by_same_item_collapse():
    spec = dict(material="stainless", form="sheet", thickness_in=0.0781, width_in=48,
                length_in=96, standard="ASTM A240")
    amb = issue("ambiguous_options", "304 or 304L?", "grade", ["304", "304L"])
    line = resolve(make(spec, [amb]), ctx())
    assert [o.candidate.sku for o in line.offers] == ["SS-304L-SHT-0781-48X96"]
    assert line.offers[0].label == "As requested"


def test_tie_between_finishes():
    spec = dict(material="stainless", grade="304", form="sheet", thickness_in=0.125,
                width_in=48, length_in=120, standard="ASTM A240")
    line = resolve(make(spec), ctx())
    assert {o.candidate.sku for o in line.offers} == {"SS-304L-SHT-1250-48X120-2B",
                                                      "SS-304L-SHT-1250-48X120-4"}
    assert sorted(o.label for o in line.offers) == ["Option A: 304/304L, 2B finish",
                                                    "Option B: 304/304L, #4 finish"]
    tie = next(i for i in line.issues if i.kind == "tie")
    assert tie.options == ["2B finish", "#4 finish"]


def test_stated_finish_breaks_the_tie():
    spec = dict(material="stainless", grade="304", form="sheet", thickness_in=0.125,
                width_in=48, length_in=120, finish="#4")
    line = resolve(make(spec), ctx())
    assert [o.candidate.sku for o in line.offers] == ["SS-304L-SHT-1250-48X120-4"]
    assert "tie" not in kinds(line)


def test_weak_match_on_standard_mismatch():
    spec = dict(material="carbon", grade="A36", form="plate", thickness_in=0.25, width_in=48,
                length_in=96, standard="ASTM A572")
    line = resolve(make(spec), ctx())
    assert line.offers[0].candidate.strength < 0.8
    weak = next(i for i in line.issues if i.kind == "weak_match")
    assert weak.audience == "internal"


def test_cross_reference_resolves_for_that_customer_only():
    line = resolve(make({"quantity": 20, "quantity_unit": "ea"}, part_no="ACME-PN 88213"),
                   ctx("Acme Fabrication"))
    offer = line.offers[0]
    assert offer.candidate.via == "cross_reference" and offer.candidate.strength == 1.0
    assert offer.candidate.sku == "SS-304L-RB-1000-144"
    assert (offer.spec.form, offer.spec.diameter_in, offer.spec.quantity) == ("round_bar", 1.0, 20)
    assert offer.spec.grade == "304/304L" and offer.spec.standard == "ASTM A276"
    assert line.issues == []

    other = resolve(make({"quantity": 20, "quantity_unit": "ea"}, part_no="88213"),
                    ctx("Brightline Manufacturing"))
    assert other.offers[0].candidate.sku == "CS-1018-RB-1000-144"


def test_unknown_part_number_without_description_asks():
    line = resolve(make({"quantity": 5}, part_no="ZZ-1"), ctx())
    assert line.offers == []
    assert kinds(line) == ["missing"] and line.issues[0].audience == "buyer"


def test_unknown_part_number_with_description_falls_back_to_spec():
    line = resolve(make(SHEET_16GA | {"grade": "316"}, part_no="ZZ-1"), ctx())
    assert line.offers[0].candidate.via == "spec"


def test_blocking_issue_from_earlier_stage_leaves_line_alone():
    conflict = issue("conflict", "16 ga is not 0.075 in", "thickness")
    line = resolve(make(SHEET_16GA | {"grade": "304"}, [conflict]), ctx())
    assert line.offers == [] and kinds(line) == ["conflict"]
    missing = issue("missing", "length?", "length")
    line = resolve(make(SHEET_16GA | {"grade": "304"}, [missing]), ctx())
    assert line.offers == [] and kinds(line) == ["missing"]


def test_non_blocking_missing_does_not_stop_matching():
    line = resolve(make(SHEET_16GA | {"grade": "316"}, [issue("missing", "qty?", "quantity")]),
                   ctx())
    assert len(line.offers) == 1


def test_not_in_catalog_is_no_match_with_reason():
    spec = dict(form="plate", thickness_in=0.375, quantity=3)
    line = resolve(make(spec, grade_text="Inconel 625"), ctx())
    assert line.offers == []
    assert kinds(line) == ["no_match"]
    assert "Inconel 625" in line.issues[0].message and line.issues[0].audience == "buyer"


def test_known_grade_in_unstocked_size_is_no_match():
    spec = dict(material="carbon", grade="A36", form="plate", thickness_in=0.25, width_in=60,
                length_in=120)
    line = resolve(make(spec), ctx())
    assert line.offers == [] and kinds(line) == ["no_match"]
    assert "size" in line.issues[0].message


def test_substitute_grade_is_labeled_never_the_match():
    spec = dict(material="aluminum", grade="3003-H14", form="sheet", thickness_in=0.05,
                width_in=48, length_in=96)
    line = resolve(make(spec), ctx())
    assert [o.label for o in line.offers] == ["Substitute: 5052-H32"]
    assert line.offers[0].spec.grade == "5052-H32"
    assert kinds(line) == ["substitution"]


def test_no_cost_or_supplier_in_buyer_text():
    ref = load_reference()
    suppliers = {i.supplier.lower() for i in ref.catalog}
    amb = issue("ambiguous_options", "Which?", "grade", ["304", "316"])
    for line in (resolve(make(SHEET_16GA | {"grade": "304H"}), ctx()),
                 resolve(make(SHEET_16GA, [amb]), ctx())):
        texts = [o.label for o in line.offers] + [i.message for i in line.issues
                                                  if i.audience == "buyer"]
        for t in texts:
            assert not any(s in t.lower() for s in suppliers) and "cost" not in t.lower()


def _golden_cases():
    rows = [json.loads(l) for l in GOLDEN.read_text().splitlines() if l.strip()]
    return [r for r in rows if r["kind"] == "item" and r["expected"].get("spec")
            and r["expected"]["skus"] and r["expected"]["spec"].get("grade")
            and r["id"] not in {"email-4"}]


@pytest.mark.parametrize("row", _golden_cases(), ids=lambda r: r["id"])
def test_golden_lines_find_expected_skus(row):
    spec = {k: v for k, v in row["expected"]["spec"].items() if v is not None}
    line = resolve(make(spec), ctx(row["customer"]))
    assert sorted(o.candidate.sku for o in line.offers) == sorted(row["expected"]["skus"])
