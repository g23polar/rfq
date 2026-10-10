from datetime import date
from pathlib import Path

import pytest

from rfq.context import Context
from rfq.decide import STATUS_RULES, assign_status, decide, email_questions
from rfq.models import (ISSUE_AUDIENCE, Candidate, Line, Offer, Price, Run, Segment, Spec, issue)
from rfq.reference import load_reference

SAMPLE = Path(__file__).parent.parent / "fixtures" / "sample_run.json"


@pytest.fixture
def run() -> Run:
    return Run.model_validate_json(SAMPLE.read_text())


@pytest.fixture
def ctx(run) -> Context:
    return Context(terms=run.terms, ref=load_reference(), today=date(2026, 10, 10))


def priced_offer(label="As requested") -> Offer:
    price = Price(unit="ea", unit_price=10, extended=10, weight_lb=1, valid_until="2026-10-17",
                  cost_per_lb=1, margin_pct=20, floor_margin_pct=12)
    return Offer(label=label, spec=Spec(), candidate=Candidate(sku="X", description="x", strength=1),
                 price=price)


def make(issues=(), offers=1, kind="item", priced=True, no="7") -> Line:
    offs = [priced_offer(f"Option {n}") for n in range(offers)]
    if not priced:
        for o in offs:
            o.price = None
    return Line(buyer_line_no=no, segment=Segment(buyer_line_no=no, text="x", kind=kind),
                issues=list(issues), offers=offs)


def status(*issues, **kw):
    return decide(make(issues, **kw), None).status


def test_every_sample_line_gets_the_status_it_was_built_with(run, ctx):
    for line in run.lines:
        expected = line.status
        line.status = None
        assert decide(line, ctx).status == expected, line.buyer_line_no


def test_rule_table_is_ordered_and_complete():
    assert [r.order for r in STATUS_RULES] == list(range(1, len(STATUS_RULES) + 1))
    assert {r.status for r in STATUS_RULES} == {"not_an_item", "needs_specialist_review", "no_bid",
                                                "needs_buyer_input", "quoted_with_alternates",
                                                "quoted_with_assumptions", "quoted"}


@pytest.mark.parametrize("kind", ["below_floor", "weak_match", "paths_disagree", "withheld_text",
                                  "unconfirmed", "verification_failed", "model_failed"])
def test_rule_2_each_internal_kind_sends_the_line_to_review(kind):
    assert status(issue(kind, "internal")) == "needs_specialist_review"


def test_rule_1_wins_over_everything():
    assert status(issue("below_floor", "x"), kind="requirement") == "not_an_item"


def test_rule_2_wins_over_no_bid_and_buyer_input():
    assert status(issue("no_match", "x"), issue("weak_match", "y"), offers=0) \
        == "needs_specialist_review"
    assert status(issue("missing", "x"), issue("unconfirmed", "y"), offers=0) \
        == "needs_specialist_review"


def test_rule_3_no_bid_from_no_match_or_unmet_requirement():
    assert status(issue("no_match", "We do not stock it."), offers=0) == "no_bid"
    assert status(issue("unmet_requirement", "None comply."), offers=2) == "no_bid"


def test_rule_3_missing_or_conflict_without_offers_is_buyer_input_not_no_bid():
    assert status(issue("missing", "no unit", "length"), offers=0) == "needs_buyer_input"
    assert status(issue("conflict", "two sizes"), offers=0) == "needs_buyer_input"
    assert status(issue("missing_attachment", "see drawing"), offers=0) == "needs_buyer_input"
    assert status(issue("ambiguous_options", "grade", "grade"), offers=0) == "needs_buyer_input"


def test_rule_3_item_with_no_offers_and_nothing_to_ask_is_no_bid():
    assert status(offers=0) == "no_bid"
    assert status(issue("assumption", "x"), offers=0) == "no_bid"


def test_no_match_beats_missing():
    assert status(issue("missing", "x"), issue("no_match", "y"), offers=0) == "no_bid"


def test_rule_4_buyer_input_even_with_a_priced_offer():
    assert status(issue("missing", "x")) == "needs_buyer_input"


def test_rule_5_alternates_need_a_priced_offer():
    for kind in ("ambiguous_options", "tie", "substitution"):
        assert status(issue(kind, "x"), offers=2) == "quoted_with_alternates"
        assert status(issue(kind, "x"), offers=2, priced=False) == "needs_buyer_input"


def test_rule_6_assumption_or_open_question_only():
    assert status(issue("assumption", "x")) == "quoted_with_assumptions"
    assert status(issue("open_question", "x")) == "quoted_with_assumptions"


def test_rule_7_quoted_and_note_only_kinds_do_not_change_it():
    assert status() == "quoted"
    line = decide(make([issue("price_out_of_range", "Above the range."),
                        issue("stale_benchmark", "Benchmark is old.")]), None)
    assert line.status == "quoted"
    assert line.review_note == "Above the range. Benchmark is old."


def test_priced_status_requires_a_priced_offer():
    assert status(offers=1, priced=False) == "needs_specialist_review"


def test_every_kind_combination_yields_exactly_one_status():
    kinds = list(ISSUE_AUDIENCE)
    for k in kinds:
        for offers in (0, 1):
            assert status(issue(k, "m"), offers=offers) is not None


def test_review_note_for_review_lines_and_none_otherwise(run, ctx):
    by_no = {l.buyer_line_no: l for l in run.lines}
    assert "5.3%" in decide(by_no["50"], ctx).review_note
    assert decide(by_no["10"], ctx).review_note is None


def test_internal_issues_never_produce_a_question():
    line = decide(make([issue("below_floor", "Margin too low."), issue("weak_match", "meh")]), None)
    assert line.question is None
    line = decide(make([issue("price_out_of_range", "far"), issue("assumption", "a")]), None)
    assert line.question is None and "far" in line.review_note


def test_missing_question_with_options_is_blocking():
    line = decide(make([issue("missing", 'Length "12" has no unit.', "length",
                              ["12 inches", "12 feet"])], offers=0, no="40"), None)
    q = line.question
    assert q.blocking and q.options == ["12 inches", "12 feet"]
    assert q.text.startswith("Line 40: Length \"12\" has no unit. Please provide")
    assert "12 inches, 12 feet" in q.text


def test_alternates_question_lists_options_and_is_not_blocking(run, ctx):
    line = run.lines[2]
    line.issues[0].options = ["304/304L", "316/316L"]
    line = decide(line, ctx)
    assert line.status == "quoted_with_alternates"
    assert line.question.options == ["304/304L", "316/316L"] and not line.question.blocking
    assert "Line 30" in line.question.text and "304/304L, 316/316L" in line.question.text


def test_several_open_items_become_one_question_with_the_top_items_options():
    line = decide(make([issue("open_question", "Is a mill cert needed?"),
                        issue("missing", "No length given.", "length", ["12 in", "12 ft"]),
                        issue("assumption", "ignored assumption")], offers=0), None)
    q = line.question
    assert q.options == ["12 in", "12 ft"]
    assert q.text.index("No length given.") < q.text.index("Is a mill cert needed?")
    assert "ignored assumption" not in q.text


def test_no_question_for_assumptions_only_or_no_bid():
    assert decide(make([issue("assumption", "a")]), None).question is None
    assert decide(make([issue("no_match", "none")], offers=0), None).question is None


def test_decide_is_repeatable():
    line = make([issue("missing", "No unit.")], offers=0)
    first = decide(line, None).model_copy(deep=True)
    assert decide(line, None) == first


def test_email_order_blocking_first_then_priced_lines(run, ctx):
    for line in run.lines:
        decide(line, ctx)
    order = email_questions(run)
    assert [no for no, _ in order] == ["40", "30"]
    assert [q.blocking for _, q in order] == [True, False]
    a, b = make(no="1"), make(no="2")
    a.question = b_q = decide(make([issue("ambiguous_options", "x")], offers=2), None).question
    b.question = decide(make([issue("missing", "y")], offers=0), None).question
    assert [no for no, _ in email_questions(Run(rfq_id="r", created="c", source=run.source,
                                                lines=[a, b]))] == ["2", "1"]
    assert b_q.blocking is False
