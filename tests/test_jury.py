"""Model jury: a second model's reading, standardized and compared with the first."""
from datetime import date

import pytest

from rfq import interpret, pipeline
from rfq.context import Context
from rfq.interpret import LineReading, Quoted
from rfq.llm import MODEL_READ, ModelCallError, ModelResult
from rfq.models import Line, Reading, Segment, Sourced, Terms, buyer_view, Run, RunSource
from rfq.reference import load_reference

TEXT = "304 SS sheet 16ga 4x8 - 10 ea"
JURY = "openai/some-model"


def s(value, unit=None, text=None):
    return Sourced(value=value, unit=unit, source_text=text or str(value))


def reading(grade="304", qty="10", gauge=("16", "ga")):
    return Reading(grade=s(grade), material=s("SS"), form=s("sheet"),
                   gauge=s(gauge[0], gauge[1], text="16ga"),
                   unlabeled_dimensions=[s("4", text="4x8"), s("8", text="4x8")],
                   quantity=s(qty, "ea", text=f"{qty} ea"))


@pytest.fixture
def ctx():
    return Context(terms=Terms(), ref=load_reference(), today=date(2026, 10, 10))


@pytest.fixture(autouse=True)
def jury_on(monkeypatch):
    monkeypatch.setenv("RFQ_JURY_MODEL", JURY)


def run_line(first, second, ctx, text=TEXT):
    line = Line(buyer_line_no="1", segment=Segment(buyer_line_no="1", text=text),
                reading=first, second_reading=second)
    return pipeline._rule_stages(line, ctx, pipeline.Trace())


def test_agreeing_readings_quote_as_before_and_mark_the_match(ctx):
    line = run_line(reading(), reading(), ctx)
    assert line.jury.agreed and line.jury.differences == []
    assert line.jury.model == JURY
    assert "paths_disagree" not in {i.kind for i in line.issues}
    assert line.status == "quoted_with_assumptions"
    assert all(o.candidate.paths_agree for o in line.offers)


def test_a_different_grade_holds_the_line_for_the_specialist(ctx):
    line = run_line(reading(grade="304"), reading(grade="304H"), ctx)
    assert not line.jury.agreed
    assert any(d.startswith("grade:") for d in line.jury.differences)
    assert line.status == "needs_specialist_review"
    problem = next(i for i in line.issues if i.kind == "paths_disagree")
    assert problem.audience == "internal"
    assert "304" in problem.message and "some-model" in problem.message
    assert all(o.candidate.paths_agree is False for o in line.offers)


def test_a_different_quantity_is_a_disagreement(ctx):
    line = run_line(reading(qty="10"), reading(qty="100"), ctx)
    assert "quantity: 10 / 100" in line.jury.differences
    assert line.status == "needs_specialist_review"


def test_how_a_model_writes_a_value_down_does_not_count(ctx):
    # "16" + "ga" vs "16ga" with no unit; "4x8" vs labeled width and length in inches.
    second = Reading(grade=s("304"), material=s("SS"), form=s("sheet"),
                     gauge=s("16ga", text="16ga"), width=s("48", "in", text="4x8"),
                     length=s("96", "in", text="4x8"), quantity=s("10", text="10 ea"))
    line = run_line(reading(), second, ctx)
    assert line.jury.agreed, line.jury.differences


def test_no_second_reading_leaves_the_line_alone(ctx):
    line = run_line(reading(), None, ctx)
    assert line.jury is None
    assert line.status == "quoted_with_assumptions"


def test_a_disagreeing_line_never_reaches_the_buyer(ctx):
    line = run_line(reading(grade="304"), reading(grade="316"), ctx)
    run = Run(rfq_id="Q-1", created="2026-10-10", source=RunSource(kind="text"), lines=[line])
    assert buyer_view(run).lines == []


# --- interpret: both models read the line ---------------------------------------------

def fake_call(answers):
    def call_json(system, user, shape, model, max_tokens=None):
        answer = answers[model]
        if isinstance(answer, Exception):
            raise answer
        return ModelResult(answer)
    return call_json


def q(value, unit=None, text=None):
    return Quoted(value=value, unit=unit, source_text=text or value)


def line_reading(grade):
    return LineReading(grade=q(grade), material=q("SS"), form=q("sheet"),
                       gauge=q("16", "ga", "16ga"), quantity=q("10", "ea", "10 ea"))


def item():
    return Line(buyer_line_no="1", segment=Segment(buyer_line_no="1", text=TEXT))


def test_interpret_keeps_both_readings(monkeypatch):
    monkeypatch.setattr(interpret, "call_json",
                        fake_call({MODEL_READ: line_reading("304"), JURY: line_reading("304")}))
    line = interpret.interpret(item(), Terms())
    assert line.reading.grade.value == "304"
    assert line.second_reading.grade.value == "304"


def test_the_second_reading_is_held_to_the_same_source_check(monkeypatch):
    invented = line_reading("304")
    invented.grade = q("316", text="316 SS")  # not in the line
    monkeypatch.setattr(interpret, "call_json",
                        fake_call({MODEL_READ: line_reading("304"), JURY: invented}))
    line = interpret.interpret(item(), Terms())
    assert line.second_reading.grade is None
    assert line.second_reading.discarded[0].field == "grade"


def test_a_failing_jury_model_does_not_stop_the_line(monkeypatch):
    monkeypatch.setattr(interpret, "call_json", fake_call(
        {MODEL_READ: line_reading("304"), JURY: ModelCallError("gateway down")}))
    line = interpret.interpret(item(), Terms())
    assert line.reading.grade.value == "304"
    assert line.second_reading is None
    assert not line.issues


def test_jury_off_makes_one_call(monkeypatch):
    monkeypatch.delenv("RFQ_JURY_MODEL")
    seen = []

    def call_json(system, user, shape, model, max_tokens=None):
        seen.append(model)
        return ModelResult(line_reading("304"))
    monkeypatch.setattr(interpret, "call_json", call_json)
    line = interpret.interpret(item(), Terms())
    assert seen == [MODEL_READ] and line.second_reading is None
