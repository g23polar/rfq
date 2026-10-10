"""Spreadsheet RFQs: read into labeled text without a model, then through the usual pipeline."""
from datetime import date
from pathlib import Path

import pytest

from rfq import pipeline
from rfq.context import Context
from rfq.intake import read_document
from rfq.models import Line, Reading, Segment, Sourced, Terms
from rfq.reference import load_reference
from rfq.standardize import standardize

ROOT = Path(__file__).parent.parent
SHEET = ROOT / "fixtures" / "rfq.xlsx"


def test_xlsx_becomes_one_labeled_line_per_row():
    doc = read_document(SHEET.read_bytes(), "rfq.xlsx")
    assert doc.source.kind == "spreadsheet"
    lines = doc.cleaned.splitlines()
    assert lines[:4] == ["Customer: Acme Fabrication", "RFQ: 2026-1152", "Quote due: 2026-10-16",
                         "Buyer: Dana Whitfield"]
    assert lines[4] == ("Line 10 | Description: 5052-H32 AL sheet .050 x 48 x 96 | "
                        "Qty: 10 / 50 / 100 | UoM: ea | Notes: Price @ each quantity")
    assert lines[6] == "Line 30 | Description: 304 SS round tube 1 OD x .065 wall x 20 ft | Qty: 25 | UoM: ea"
    assert "Line | Description" not in doc.cleaned  # the header row is used, not repeated


def test_empty_quantity_cell_is_written_as_blank_not_dropped():
    """Without this, the line number could be mistaken for the quantity."""
    doc = read_document(SHEET.read_bytes(), "rfq.xlsx")
    assert "Line 20 | Description: 1018 CRS rd bar 1/2 dia x 12 ft | Qty: (blank) | UoM: ea" in doc.cleaned


def test_each_text_line_maps_back_to_its_sheet_row():
    doc = read_document(SHEET.read_bytes(), "rfq.xlsx")
    assert [r for r, _, _ in doc.rows] == [1, 2, 3, 4, 7, 8, 9]  # row 5 is empty, row 6 the header
    assert doc.row_at(doc.cleaned.index("Line 30")) == 9
    assert doc.row_at(doc.cleaned.index("Customer")) == 1


def test_csv_is_read_the_same_way():
    doc = read_document("Customer,Acme\n\nLine,Description,Qty,UoM\n1,304 SS sheet 16ga 4x8,10,ea\n"
                        "2,A36 plate 1/4 x 48 x 96,,ea\n", "rfq.csv")
    assert doc.source.kind == "spreadsheet"
    assert doc.cleaned.splitlines() == [
        "Customer Acme", "Line 1 | Description: 304 SS sheet 16ga 4x8 | Qty: 10 | UoM: ea",
        "Line 2 | Description: A36 plate 1/4 x 48 x 96 | Qty: (blank) | UoM: ea"]


def test_a_sheet_with_no_table_is_still_readable_text():
    doc = read_document("please quote 304 SS sheet 16ga 4x8 qty 10\n", "note.csv")
    assert doc.cleaned.strip() == "please quote 304 SS sheet 16ga 4x8 qty 10"


def _line(text, quantity=None):
    reading = Reading(grade=Sourced(value="5052-H32"), form=Sourced(value="sheet"),
                      thickness=Sourced(value=".050", unit="in"), width=Sourced(value="48", unit="in"),
                      length=Sourced(value="96", unit="in"), quantity=quantity)
    ctx = Context(terms=Terms(), ref=load_reference(), today=date(2026, 10, 10))
    return standardize(Line(buyer_line_no="10", segment=Segment(buyer_line_no="10", text=text),
                            reading=reading), ctx)


def test_quantity_breaks_ask_which_quantity_instead_of_saying_none_was_given():
    line = _line("Description: 5052-H32 AL sheet .050 x 48 x 96 | Qty: 10 / 50 / 100 | UoM: ea")
    issue = next(i for i in line.issues if i.field == "quantity")
    assert issue.kind == "missing" and issue.options == ["10", "50", "100"]
    assert "10 / 50 / 100" in issue.message and "No quantity was given" not in issue.message


def test_quantity_breaks_read_as_a_quantity_are_priced_once_and_say_so():
    line = _line("Description: ... | Qty: 10 / 50 / 100 | UoM: ea",
                 quantity=Sourced(value="10 / 50 / 100", unit="ea"))
    assert line.spec.quantity == 10
    note = next(i for i in line.issues if i.field == "quantity")
    assert note.kind == "assumption" and "prices 10 only" in note.message


def test_a_fraction_or_grade_is_not_mistaken_for_quantity_breaks():
    line = _line("304/304L SS rd bar 1/2 dia x 12 ft")
    issue = next(i for i in line.issues if i.field == "quantity")
    assert issue.options == [] and issue.message.startswith("No quantity was given")


def test_spreadsheet_runs_through_the_whole_pipeline(monkeypatch):
    monkeypatch.setenv("RFQ_LLM_CACHE", str(ROOT / "tests" / "recordings"))
    done = pipeline.process(SHEET.read_bytes(), "rfq.xlsx", today=date(2026, 10, 10))
    run = done.run
    assert all(c.source == "cache" for c in done.trace.calls)
    assert run.source.kind == "spreadsheet" and run.terms.customer.value == "Acme Fabrication"
    by_no = {l.buyer_line_no: l for l in run.lines}
    assert set(by_no) == {"10", "20", "30"}  # the buyer's own numbering
    assert [by_no[n].segment.location.row for n in ("10", "20", "30")] == [7, 8, 9]
    assert by_no["20"].status == "needs_buyer_input"  # no quantity: asked, never guessed
    assert by_no["20"].spec.quantity is None
    assert by_no["30"].status == "quoted_with_assumptions"
    assert by_no["30"].offers[0].candidate.sku == "SS-304L-RT-1000X065-240"
    assert by_no["10"].status in ("needs_buyer_input", "quoted_with_assumptions")
    assert run.leak_check.passed
