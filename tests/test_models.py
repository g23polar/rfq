from pathlib import Path
from typing import get_args

import pytest

from rfq.models import (ISSUE_AUDIENCE, IssueKind, LineStatus, Run, buyer_view, issue)

SAMPLE = Path(__file__).parent.parent / "fixtures" / "sample_run.json"


@pytest.fixture(scope="module")
def run() -> Run:
    return Run.model_validate_json(SAMPLE.read_text())


def test_sample_run_has_every_status(run):
    assert {line.status for line in run.lines} == set(get_args(LineStatus))
    assert run.counts == {s: 1 for s in get_args(LineStatus)}


def test_sample_run_has_alternates_and_withheld_text(run):
    alternates = next(l for l in run.lines if l.status == "quoted_with_alternates")
    assert len(alternates.offers) >= 2 and all(o.price for o in alternates.offers)
    assert alternates.question and not alternates.question.blocking
    assert len(run.withheld) == 1


def test_sample_rationale_numbers_are_in_the_rationale(run):
    for line in run.lines:
        for offer in line.offers:
            if offer.price:
                assert f"{offer.price.numbers['price_per_lb']:.4f}" in offer.price.rationale
                assert "synthetic" in offer.price.rationale


def test_every_issue_kind_has_an_audience():
    assert set(ISSUE_AUDIENCE) == set(get_args(IssueKind))
    assert issue("below_floor", "x").audience == "internal"
    assert issue("missing", "x").audience == "buyer"


def test_buyer_view_drops_the_line_in_specialist_review(run):
    quote = buyer_view(run)
    held = next(l for l in run.lines if l.status == "needs_specialist_review")
    assert held.buyer_line_no not in {l.buyer_line_no for l in quote.lines}
    assert len(quote.lines) == len(run.lines) - 1


def test_buyer_view_has_no_internal_data(run):
    text = buyer_view(run).model_dump_json()
    for key in ("cost_per_lb", "margin_pct", "floor_margin_pct", "review_note", "withheld",
                "issues", "strength"):
        assert key not in text
    for line in run.lines:
        if line.review_note:
            assert line.review_note not in text
        for i in line.issues:
            if i.audience == "internal":
                assert i.message not in text
        for offer in line.offers:
            if offer.price:
                assert f'{offer.price.cost_per_lb}' not in text.replace(
                    f'{offer.price.unit_price}', "")
    for w in run.withheld:
        assert w.text not in text


def test_buyer_view_prices_only_what_the_buyer_may_see(run):
    quote = buyer_view(run)
    by_no = {l.buyer_line_no: l for l in quote.lines}
    assert by_no["40"].offers == [] and by_no["40"].question.blocking
    assert by_no["60"].offers == [] and "C276" in by_no["60"].reason
    assert len(by_no["30"].offers) == 2
    assert len(by_no["10"].assumptions) == 3
    # Total counts single-offer priced lines only: not alternates, not the held line.
    assert quote.total == round(by_no["10"].offers[0].price.extended
                                + by_no["20"].offers[0].price.extended, 2)
    assert quote.total == run.total
