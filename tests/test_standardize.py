"""Standardize stage tests (plans/08-standardize.md). Readings are built by hand."""

import json
from datetime import date
from pathlib import Path

import pytest

from rfq.context import Context
from rfq.models import Line, Reading, Segment, Sourced, Terms
from rfq.reference import load_reference
from rfq.standardize import standardize

CTX = Context(terms=Terms(), ref=load_reference(), today=date(2026, 10, 10))


def S(value, unit=None):
    return Sourced(value=value, unit=unit)


def run(**fields):
    dims = [S(*d) if isinstance(d, tuple) else S(d) for d in fields.pop("unlabeled", [])]
    reading = Reading(unlabeled_dimensions=dims,
                      **{k: (v if isinstance(v, Sourced) else S(*v) if isinstance(v, tuple)
                             else S(v)) for k, v in fields.items()})
    line = Line(buyer_line_no="1", segment=Segment(buyer_line_no="1", text="x"), reading=reading)
    return standardize(line, CTX)


def kinds(line):
    return [i.kind for i in line.issues]


def test_not_an_item_or_no_reading_is_untouched():
    line = Line(buyer_line_no="1", segment=Segment(buyer_line_no="1", text="x", kind="note"),
                reading=Reading(quantity=S("1")))
    assert standardize(line, CTX).spec is None
    line = Line(buyer_line_no="1", segment=Segment(buyer_line_no="1", text="x"))
    assert standardize(line, CTX).spec is None


def test_track_examples_share_fingerprint():
    a = run(material="SS", grade="304", form="sheet", gauge=("16", "ga"),
            unlabeled=["4", "8"], quantity=("10", "ea"))
    b = run(material="Stainless", grade="304", form="sheet", thickness=("0.060", "in"),
            unlabeled=["48", "96"], quantity=("6", "ea"))
    assert a.spec.fingerprint == b.spec.fingerprint
    assert a.spec.thickness_in == 0.0625 and a.spec.width_in == 48 and a.spec.length_in == 96
    assert a.spec.standard == "ASTM A240"
    assert "assumption" in kinds(a) and "assumption" in kinds(b)
    assert any("feet" in i.message for i in a.issues)
    assert any("standard 0.0625" in i.message for i in b.issues)


def test_gauge_differs_by_material():
    vals = {}
    for mat, grade in (("stainless", "304"), ("carbon", "1008"), ("aluminum", "5052-H32")):
        l = run(material=mat, grade=grade, form="sheet", gauge="16ga",
                width=("48", "in"), length=("96", "in"), quantity="1")
        vals[mat] = l.spec.thickness_in
    assert len(set(vals.values())) == 3
    assert vals["aluminum"] == 0.0508


def test_gauge_without_material_is_missing_grade():
    l = run(form="sheet", gauge=("16", "ga"), width=("48", "in"), length=("96", "in"),
            quantity="1")
    assert any(i.kind == "missing" and i.field == "grade" for i in l.issues)
    assert l.spec.thickness_in is None


def test_unlabeled_smallest_is_thickness():
    l = run(material="AL", grade="6061-T6", form="plate", unlabeled=["48", ".25", "96"],
            standard="ASTM B209", quantity="3")
    assert (l.spec.thickness_in, l.spec.width_in, l.spec.length_in) == (0.25, 48, 96)
    assert any(i.kind == "assumption" and "not labeled" in i.message for i in l.issues)


def test_fraction_forms():
    for text in ("1-1/2", "1 1/2", "1.5", "1½"):
        l = run(material="SS", grade="304", form="round bar", diameter=(text, '"'),
                length=("12", "ft"), quantity=("5", "pcs"))
        assert l.spec.diameter_in == 1.5, text
        assert l.spec.length_in == 144
        assert l.spec.form == "round_bar"
        assert l.spec.quantity_unit == "ea"


def test_unit_conversion_mm():
    l = run(material="SS", grade="316", form="plate", thickness=("6.35", "mm"),
            width=("1219.2", "mm"), length=("96", "in"), quantity="1")
    assert l.spec.thickness_in == 0.25 and l.spec.width_in == 48


def test_gauge_and_decimal_agree_or_conflict():
    ok = run(material="SS", grade="304", form="sheet", gauge="16 ga", thickness=("0.060", "in"),
             width=("48", "in"), length=("96", "in"), quantity="1")
    assert ok.spec.thickness_in == 0.0625 and "conflict" not in kinds(ok)
    bad = run(material="SS", grade="304", form="sheet", gauge="16 ga",
              thickness=("0.075", "in"), width=("48", "in"), length=("96", "in"), quantity="1")
    assert bad.spec.thickness_in is None
    conflict = [i for i in bad.issues if i.kind == "conflict"]
    assert conflict and conflict[0].audience == "buyer"


def test_missing_grade_is_ambiguous_options():
    l = run(material="Stainless", form="sheet", gauge="16ga", unlabeled=["4", "8"], quantity="12")
    amb = [i for i in l.issues if i.kind == "ambiguous_options"]
    assert amb and amb[0].field == "grade" and amb[0].options == ["304", "316"]
    assert "missing" not in kinds(l)


def test_unclear_grade_variants():
    l = run(material="SS", grade="304 or 304L?", form="sheet", gauge="14 ga",
            unlabeled=["48", "96"], standard="ASTM A240", quantity="6")
    amb = [i for i in l.issues if i.kind == "ambiguous_options"]
    assert amb[0].options == ["304", "304L"] and l.spec.grade is None
    assert l.spec.thickness_in == 0.0781
    l2 = run(material="SS", grade="304/L?", form="sheet", gauge="14", quantity="1")
    assert [i.options for i in l2.issues if i.kind == "ambiguous_options"] == [["304", "304L"]]


def test_grade_variants_kept():
    for written, want in (("304H", "304H"), ("304L", "304L"), ("304", "304"),
                          ("304/304L", "304"), ("C1018", "1018")):
        l = run(grade=written, form="round_bar", diameter=("1", "in"), length=("12", "ft"),
                quantity="1")
        assert l.spec.grade == want, written


def test_material_grade_conflict():
    l = run(material="aluminum", grade="304", form="sheet", gauge="16", quantity="1")
    c = [i for i in l.issues if i.kind == "conflict"]
    assert c and c[0].audience == "buyer"


def test_shorthand_and_finish():
    l = run(material="HRP&O", grade="1011", form="sht", gauge="10ga", unlabeled=['48"', '96"'],
            quantity="15")
    assert l.spec.material == "carbon" and l.spec.finish == "HRP&O"
    assert l.spec.form == "sheet" and l.spec.thickness_in == 0.1345
    assert l.spec.standard == "ASTM A1011"
    l = run(material="CRS", grade="1018", form="rd bar", diameter=("1", "in"),
            length=("12", "ft"), quantity=("1,500", "lbs"))
    assert l.spec.quantity == 1500 and l.spec.quantity_unit == "lb"
    assert l.spec.finish == "cold rolled" and l.spec.standard == "ASTM A108"


@pytest.mark.parametrize("raw,unit,want", [("500", "#", "lb"), ("5", "cwt", "cwt"),
                                           ("40", "ft", "ft"), ("3", None, "ea")])
def test_quantity_units(raw, unit, want):
    l = run(grade="1018", form="round_bar", diameter=("1", "in"), length=("12", "ft"),
            quantity=(raw, unit))
    assert l.spec.quantity_unit == want


def test_missing_quantity():
    l = run(material="SS", grade="304", form="round_bar", diameter=("1", "in"),
            length=("12", "ft"))
    assert [i.field for i in l.issues if i.kind == "missing"] == ["quantity"]


def test_bare_length_is_missing_and_bare_diameter_assumed_inches():
    l = run(grade="1018", form="rd bar", diameter="1", length="12", quantity="10")
    assert l.spec.diameter_in == 1.0 and l.spec.length_in is None
    assert [i.field for i in l.issues if i.kind == "missing"] == ["length"]
    assert any(i.kind == "assumption" and i.field == "diameter" for i in l.issues)


def test_bare_size_not_standard_is_missing():
    l = run(material="SS", grade="304", form="sheet", gauge="16", unlabeled=["30", "61"],
            quantity="1")
    assert any(i.kind == "missing" and i.field == "width" for i in l.issues)
    assert l.spec.width_in is None


def test_tube_wall_and_square():
    l = run(material="SS", grade="304", form="square tube", width=("1", "in"),
            wall=(".065", "in"), length=("20", "ft"), quantity="10")
    assert l.spec.wall_in == 0.065 and l.spec.thickness_in is None
    assert l.spec.width_in == 1 and l.spec.length_in == 240
    assert l.spec.standard == "ASTM A269"
    t = run(material="SS", grade="304", form="tube", diameter=("1", "in"), gauge="16 ga",
            length=("20", "ft"), quantity="1")
    assert t.spec.form == "round_tube" and t.spec.wall_in == 0.065


def test_missing_required_dimension():
    l = run(material="SS", grade="304", form="round_tube", diameter=("1", "in"),
            length=("20", "ft"), quantity="1")
    assert [i.field for i in l.issues if i.kind == "missing"] == ["wall"]


def test_part_number_only():
    l = run(customer_part_no="ACME-PN 88213", quantity=("20", "ea"))
    assert l.spec.quantity == 20 and l.spec.fingerprint is None
    assert l.issues == []


def test_unknown_grade_and_material_no_missing():
    l = run(grade="Inconel 625", form="plate", thickness=("3/8", "in"), width=("48", "in"),
            length=("96", "in"), quantity="3")
    assert l.spec.grade is None and l.spec.thickness_in == 0.375
    assert "missing" not in kinds(l)


def test_stated_standard_normalized():
    l = run(material="SS", grade="304", form="plate", thickness="1/4 in", unlabeled=["48 in", "96 in"],
            standard="A240", quantity="8")
    assert l.spec.standard == "ASTM A240" and l.spec.thickness_in == 0.25


def test_appends_never_removes():
    line = Line(buyer_line_no="1", segment=Segment(buyer_line_no="1", text="x"),
                reading=Reading(quantity=S("1")))
    from rfq.models import issue
    line.issues.append(issue("open_question", "earlier"))
    standardize(line, CTX)
    assert line.issues[0].message == "earlier"


GOLDEN = Path(__file__).parent.parent / "fixtures" / "golden.jsonl"


def test_golden_specs_where_reading_is_simple():
    """Spot checks against golden lines whose readings can be built unambiguously."""
    cases = {
        "email-5": dict(material="SS", grade="316", form="round bar", diameter=('1-1/2', '"'),
                        length=("12", "ft"), quantity=("4", "ea")),
        "std-3": dict(material="AL", grade="5052-H32", form="sheet", gauge="16ga",
                      unlabeled=["4", "8"], quantity="20"),
        "std-4": dict(material="CRS", grade="1008", form="sheet", gauge="16ga",
                      unlabeled=['48 in', '96 in'], standard="ASTM A1008", quantity="30"),
        "std-7": dict(material="SS", grade="316", form="sheet", gauge="18 ga",
                      unlabeled=['48 in', '96 in'], quantity="4"),
    }
    golden = {json.loads(l)["id"]: json.loads(l) for l in GOLDEN.read_text().splitlines() if l}
    for gid, fields in cases.items():
        spec = run(**fields).spec
        for key, want in golden[gid]["expected"]["spec"].items():
            assert getattr(spec, key) == want, (gid, key)


def test_every_inference_is_an_issue():
    """Each inference made is recorded: feet, default standard, snapped thickness, labels."""
    l = run(material="SS", grade="304", form="plate", unlabeled=["1/4", "4", "8"], quantity="1")
    msgs = " ".join(i.message for i in l.issues if i.kind == "assumption")
    assert "feet" in msgs
    assert "ASTM A240" in msgs
    assert "not labeled" in msgs
    assert (l.spec.thickness_in, l.spec.width_in, l.spec.length_in) == (0.25, 48, 96)
