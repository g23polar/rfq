from datetime import date
from pathlib import Path

import pytest

from rfq.context import Context
from rfq.models import Run, buyer_view, issue
from rfq.reference import load_reference
from rfq.verify import _cited_numbers, leak_check, verify

SAMPLE = Path(__file__).parent.parent / "fixtures" / "sample_run.json"


@pytest.fixture
def run() -> Run:
    return Run.model_validate_json(SAMPLE.read_text())


@pytest.fixture
def ctx(run) -> Context:
    return Context(terms=run.terms, ref=load_reference(), today=date(2026, 10, 10))


def line_of(run, no):
    return next(l for l in run.lines if l.buyer_line_no == no)


def test_every_sample_item_line_passes(run, ctx):
    for line in run.lines:
        before = line.status
        verify(line, ctx)
        if line.segment.kind == "item":
            assert line.verification.passed, (line.buyer_line_no, line.verification.failures)
        else:
            assert line.verification is None
        assert line.status == before


def test_tampered_rationale_number_fails_and_sends_line_to_review(run, ctx):
    line = line_of(run, "20")
    line.offers[0].price.rationale = line.offers[0].price.rationale.replace("3.0%", "13.0%")
    verify(line, ctx)
    assert not line.verification.passed
    assert "13" in line.verification.failures[0]
    assert line.status == "needs_specialist_review"
    assert any(i.kind == "verification_failed" and i.audience == "internal" for i in line.issues)
    assert line.question is None and "Verification failed" in line.review_note


def test_tampered_benchmark_figure_fails(run, ctx):
    line = line_of(run, "10")
    line.offers[0].price.rationale = line.offers[0].price.rationale.replace("$2.10", "$2.40")
    assert not verify(line, ctx).verification.passed


def test_rationale_tolerates_rounding_and_formatting(run, ctx):
    line = line_of(run, "10")
    price = line.offers[0].price
    price.numbers = {"a": 2.037, "b": 2.1, "c": 3.0}
    price.rationale = "Priced at $2.04/lb, 3% below the $2.100 midpoint (as of 2026-10-01, Oct 14)."
    assert verify(line, ctx).verification.passed


def test_cited_numbers_skip_dates_and_designations():
    got = _cited_numbers("304 sheet 6061-T6 ASTM A240 304L 2026-10-01 Oct 14, 2026 $2.10/lb 3.0%",
                         ["304", "6061-T6"])
    assert got == [(2.1, 2), (3.0, 1)]


def test_unsourced_spec_field_fails(run, ctx):
    line = line_of(run, "20")
    line.spec.finish = "mill"
    verify(line, ctx)
    assert not line.verification.passed and "finish" in line.verification.failures[0]
    assert line.status == "needs_specialist_review"


def test_spec_field_with_named_assumption_passes(run, ctx):
    line = line_of(run, "20")
    line.spec.finish = "mill"
    line.issues.append(issue("assumption", "Mill finish assumed.", "finish"))
    assert verify(line, ctx).verification.passed


def test_priced_line_without_a_match_fails(run, ctx):
    line = line_of(run, "20")
    line.offers[0].candidate = None
    assert not verify(line, ctx).verification.passed


def test_priced_status_with_internal_issue_fails(run, ctx):
    line = line_of(run, "20")
    line.issues.append(issue("weak_match", "meh"))
    line.status = "quoted"  # stale on purpose: priced status, yet an internal issue exists
    verify(line, ctx)
    assert not line.verification.passed and "weak_match" in line.verification.failures[0]
    assert line.status == "needs_specialist_review"


def test_verify_twice_adds_one_issue(run, ctx):
    line = line_of(run, "20")
    line.spec.finish = "mill"
    verify(line, ctx)
    verify(line, ctx)
    assert sum(i.kind == "verification_failed" for i in line.issues) == 1


def test_non_item_line_is_untouched(run, ctx):
    line = line_of(run, "-")
    assert verify(line, ctx) is line and line.verification is None


# --- leak check ---

def docs(run) -> list[str]:
    """A stand-in for the rendered quote and email: the buyer view as text."""
    return [buyer_view(run).model_dump_json(indent=1), run.email or ""]


def test_sample_buyer_documents_pass(run):
    assert leak_check(run, docs(run)) == leak_check(run, docs(run))
    result = leak_check(run, docs(run))
    assert result.passed, result.hits


def test_planted_cost_fails(run):
    cost = line_of(run, "10").offers[0].price.cost_per_lb
    result = leak_check(run, docs(run) + [f"Line 10 unit cost ${cost:.2f}/lb"])
    assert not result.passed and "cost" in result.hits[0] and "document 2" in result.hits[0]


def test_planted_margin_floor_and_percent_formats(run):
    assert not leak_check(run, ["margin 5.3%"]).passed
    assert not leak_check(run, ["we keep a 12% floor"]).passed
    assert leak_check(run, ["12 inches on line 40"]).passed


def test_cost_equal_to_a_buyer_visible_figure_is_not_a_leak(run):
    line = line_of(run, "10")
    low = line.offers[0].price.benchmark.low
    line.offers[0].price.cost_per_lb = low
    assert leak_check(run, docs(run)).passed
    # ... and a figure that is not visible is still caught
    line.offers[0].price.cost_per_lb = 1.7234
    assert not leak_check(run, docs(run) + ["cost 1.72"]).passed


def test_supplier_name_fails(run):
    sup = load_reference().catalog[0].supplier
    result = leak_check(run, [f"Sourced from {sup.upper()}."])
    assert not result.passed and "supplier" in result.hits[0]


def test_review_note_withheld_text_and_internal_message_fail(run):
    note = line_of(run, "50").review_note
    assert not leak_check(run, [note]).passed
    assert not leak_check(run, [run.withheld[0].text]).passed
    assert not leak_check(run, ["Margin 5.3% is under the 12.0% floor."]).passed


def test_prices_of_a_review_line_fail(run):
    price = line_of(run, "50").offers[0].price
    assert not leak_check(run, [f"Line 50: ${price.extended:,.2f} total"]).passed
    assert not leak_check(run, [f"unit {price.unit_price:.2f}"]).passed
    assert not leak_check(run, ["SS-316L-PLT-2500-48X96"]).passed


def test_visible_sku_of_another_line_is_not_hidden(run):
    line_of(run, "50").offers[0].candidate.sku = "SS-304L-SHT-0625-48X96"
    assert leak_check(run, docs(run)).passed
