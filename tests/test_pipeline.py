"""The whole pipeline on the sample RFQs, offline, from recorded model responses.

If a prompt changes, these fail with "no saved response exists"; rerun
`uv run python scripts/record_fixtures.py`.
"""
from datetime import date
from pathlib import Path

import pytest

from rfq import pipeline, render
from rfq.models import PRICED_STATUSES, buyer_view

ROOT = Path(__file__).parent.parent
TODAY = date(2026, 10, 10)


@pytest.fixture(autouse=True)
def recorded(monkeypatch):
    monkeypatch.setenv("RFQ_LLM_CACHE", str(ROOT / "tests" / "recordings"))


def process(name, **kwargs):
    return pipeline.process((ROOT / "fixtures" / name).read_bytes(), name, today=TODAY, **kwargs)


def statuses(run):
    return {l.buyer_line_no: l.status for l in run.lines if l.status != "not_an_item"}


def prices(run):
    return {(l.buyer_line_no, o.label): (o.price.unit_price, o.price.extended)
            for l in run.lines for o in l.offers if o.price}


@pytest.fixture(scope="module")
def email():
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("RFQ_LLM_CACHE", str(ROOT / "tests" / "recordings"))
        mp.delenv("NICRRON_API_KEY", raising=False)
        return process("rfq_email.txt")


def test_email_thread_reaches_the_expected_statuses(email):
    assert statuses(email.run) == {
        "1": "quoted_with_assumptions", "2": "quoted_with_assumptions",
        "3": "quoted_with_alternates", "4": "quoted", "5": "no_bid",
        "6": "needs_specialist_review"}
    assert email.run.counts["not_an_item"] == 1
    assert email.run.completeness == "partial" and email.run.quote_status == "draft"
    assert all(c.source == "cache" for c in email.trace.calls)


def test_track_strings_become_the_same_item(email):
    one, two = email.run.lines[0], email.run.lines[1]
    assert one.spec.fingerprint == two.spec.fingerprint
    assert one.offers[0].candidate.sku == two.offers[0].candidate.sku == "SS-304L-SHT-0625-48X96"


def test_same_rfq_gives_the_same_quote_twice(email):
    again = process("rfq_email.txt").run
    assert again.rfq_id == email.run.rfq_id
    assert statuses(again) == statuses(email.run) and prices(again) == prices(email.run)
    assert again.total == email.run.total


def test_buyer_documents_hold_no_internal_data(email):
    run = email.run
    assert run.leak_check.passed, run.leak_check.hits
    held = next(l for l in run.lines if l.status == "needs_specialist_review")
    quote = render.visible_text(render.quote_html(run))
    for text in (quote, run.email):
        assert "margin" not in text.lower() and "cost" not in text.lower()
        assert held.segment.text not in text
        assert held.offers[0].candidate.sku not in text
        assert f"{held.offers[0].price.extended:,.2f}" not in text
    assert "1 line will follow separately" in run.email


def test_buyer_quote_contents(email):
    run = email.run
    quote = render.visible_text(render.quote_html(run))
    assert "DRAFT" in quote and run.rfq_id in quote and "revision 1" in quote
    assert "Prices valid until: 2026-10-17" in quote
    assert "synthetic" in quote
    assert "All material DFARS compliant" in quote
    assert "Option A" in quote and "Option B" in quote  # the missing-grade alternates
    assert "Not quoted" in quote and "not a DFARS-qualifying country" in quote
    assert f"${buyer_view(run).total:,.2f}" in quote
    run.quote_status = "approved"
    try:
        assert "DRAFT" not in render.visible_text(render.quote_html(run))
    finally:
        run.quote_status = "draft"


def test_email_lists_only_buyer_questions(email):
    text = email.run.email
    assert text.startswith(f"Subject: Quote {email.run.rfq_id}: 1 question")
    assert "4 of 6 lines priced" in text
    assert "304" in text and "316" in text  # the grade question for line 3
    assert "Line 5" in text  # the no bid, with its reason


def test_internal_summary_is_for_the_specialist(email):
    summary = render.internal_summary(email.run)
    assert "not for the buyer" in summary and "Needs specialist review" in summary
    assert "floor" in summary  # the margin note belongs here and nowhere a buyer can see


def test_trace_has_every_stage_for_every_line(email):
    names = {s.name for s in email.trace.spans}
    assert {"intake.read", "safety.screen", "intake.segment", "interpret", "questions.reword",
            *(n for n, _, _ in pipeline.RULE_STAGES)} <= names
    per_line = [s for s in email.trace.spans if s.line_no == "1"]
    assert [s.name for s in per_line] == [n for n, _, _ in pipeline.RULE_STAGES]
    assert email.trace.calls and all(c.model for c in email.trace.calls)


def test_hidden_instruction_is_withheld_and_changes_nothing():
    injected, clean = process("rfq.pdf").run, process("rfq_clean.pdf").run
    assert len(injected.withheld) == 1 and "ignore all previous instructions" in injected.withheld[0].text
    assert clean.withheld == []
    assert statuses(injected) == statuses(clean) and prices(injected) == prices(clean)
    assert injected.total == clean.total
    assert injected.withheld[0].text not in injected.email
    assert injected.withheld[0].text not in render.visible_text(render.quote_html(injected))


def test_pdf_reaches_the_expected_statuses():
    run = process("rfq.pdf").run
    assert statuses(run) == {
        "1": "needs_buyer_input", "2": "quoted_with_alternates", "3": "quoted_with_assumptions",
        "4": "quoted_with_assumptions", "5": "needs_buyer_input", "6": "no_bid", "7": "quoted",
        "8": "quoted_with_alternates"}
    short = next(l for l in run.lines if l.buyer_line_no == "4").offers[0].availability
    assert (short.status, short.available_qty, short.shortfall_qty) == ("partial", 3, 5)
    drawing = next(l for l in run.lines if l.buyer_line_no == "5")
    assert "4471" in drawing.question.text and drawing.question.blocking


def test_line_level_standards_are_not_applied_to_every_line():
    """The recorded PDF segmentation lists "ASTM A240" and "ASTM A36", each written on one
    line, as RFQ-wide requirements. They must not be demanded of every line."""
    run = process("rfq.pdf").run
    assert [str(r.value) for r in run.terms.requirements] == [
        "Mill test reports (MTRs) required for all items.",
        "Material must be new and unused; no remnants."]
    assert sum(l.status in PRICED_STATUSES for l in run.lines) == 5


def test_recorder_gets_the_run_and_its_failure_is_harmless():
    seen = []
    done = process("rfq_email.txt", recorder=lambda run, trace: seen.append((run, trace)) or "t-1")
    assert done.run.prism_trace_id == "t-1" and seen[0][0] is done.run and seen[0][1].spans

    def broken(run, trace):
        raise RuntimeError("PRISM is down")

    assert process("rfq_email.txt", recorder=broken).run.prism_trace_id is None


def test_a_stage_that_crashes_sends_only_that_line_to_review(monkeypatch):
    real = pipeline.price.price

    def flaky(line, ctx):
        if line.buyer_line_no == "4":
            raise RuntimeError("boom")
        return real(line, ctx)

    stages = tuple((n, flaky if n == "price" else f, s) for n, f, s in pipeline.RULE_STAGES)
    monkeypatch.setattr(pipeline, "RULE_STAGES", stages)
    run = process("rfq_email.txt").run
    got = statuses(run)
    assert got["4"] == "needs_specialist_review" and got["1"] == "quoted_with_assumptions"
    assert run.leak_check.passed
