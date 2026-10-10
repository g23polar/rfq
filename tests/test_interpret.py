import json
import logging
import threading

import pytest

from rfq import llm
from rfq.interpret import interpret, interpret_all
from rfq.models import Line, Segment, Sourced, Terms

DFARS = "All material DFARS compliant"
TERMS = Terms(requirements=[Sourced(value=DFARS, source_text=DFARS, source="rfq_terms")])


def q(value, source_text, unit=None):
    return {"value": value, "unit": unit, "source_text": source_text}


def item(text, no="1", kind="item"):
    return Line(buyer_line_no=no, segment=Segment(buyer_line_no=no, text=text, kind=kind))


@pytest.fixture
def model(monkeypatch):
    """Answer each interpretation call by line text; record what the model was sent."""
    replies, sent = {}, []
    lock = threading.Lock()

    def fake_send(model_name, messages, options):
        prompt = messages[-1]["content"]
        with lock:
            sent.append(prompt)
        text = prompt.split("<line>\n")[1].split("\n</line>")[0]
        reply = replies[text]
        if isinstance(reply, Exception):
            raise reply
        return json.dumps(reply), 500, 200

    monkeypatch.setenv("NICRRON_API_KEY", "test-key")
    monkeypatch.setattr(llm, "_send", fake_send)
    return replies, sent


def kept(reading):
    out = [getattr(reading, f) for f in ("material", "grade", "form", "thickness", "gauge",
                                         "width", "length", "diameter", "wall", "quantity", "standard",
                                         "finish", "temper", "tolerance", "customer_part_no",
                                         "drawing_ref")]
    return [s for s in out if s] + reading.unlabeled_dimensions + reading.requirements


def squash(text):
    return "".join(text.split()).lower()


MISSING_GRADE = "Stainless sheet 16ga 4x8 - 12 ea"


def test_missing_grade_line_has_grade_blank(model):
    replies, _ = model
    replies[MISSING_GRADE] = {
        "material": q("Stainless", "Stainless"), "form": q("sheet", "sheet"),
        "gauge": q("16", "16ga", "ga"),
        "unlabeled_dimensions": [q("4", "4x8"), q("8", "4x8")],
        "quantity": q("12", "12 ea", "ea")}
    r = interpret(item(MISSING_GRADE, "3"), TERMS).reading
    assert r.grade is None and r.standard is None
    assert (r.gauge.value, r.gauge.unit) == ("16", "ga")
    assert [d.value for d in r.unlabeled_dimensions] == ["4", "8"]
    assert r.quantity.value == "12" and not r.discarded


def test_fabricated_source_text_is_discarded_and_logged(model, caplog):
    replies, _ = model
    replies[MISSING_GRADE] = {
        "grade": q("304", "304 SS"),            # quote not in the line: made up
        "standard": q("ASTM A240", "16ga"),     # quote real, value not in it
        "gauge": q("16", "16ga", "ga")}
    with caplog.at_level(logging.WARNING, logger="rfq.interpret"):
        r = interpret(item(MISSING_GRADE), TERMS).reading
    assert r.grade is None and r.standard is None and r.gauge.value == "16"
    assert {(d.field, d.value) for d in r.discarded} == {("grade", "304"),
                                                         ("standard", "ASTM A240")}
    assert all(d.reason for d in r.discarded)
    assert "grade" in caplog.text and "standard" in caplog.text


def test_every_kept_source_text_is_in_line_or_terms(model):
    replies, _ = model
    bar = "316 SS round bar 1-1/2\" dia x 12 ft - 2 ea. DFARS not required on this line."
    replies[bar] = {
        "material": q("SS", "SS"), "grade": q("316", "316 SS"), "form": q("round bar", "round bar"),
        "diameter": q("1-1/2", "1-1/2\"  dia", "\""),  # whitespace differs: still found
        "length": q("12", "12 ft", "ft"), "quantity": q("2", "2 ea", "ea"),
        "requirements": [q("DFARS not required on this line", "DFARS not required on this line."),
                         q("DFARS compliant", "all material dfars compliant")],
        "finish": q("2B", "2B finish")}       # not in the line: dropped
    line = interpret(item(bar, "5"), TERMS)
    r = line.reading
    for s in kept(r):
        assert squash(s.source_text) in squash(bar) or squash(s.source_text) in squash(DFARS)
        assert s.source == ("rfq_line" if squash(s.source_text) in squash(bar) else "rfq_terms")
    assert r.diameter.value == "1-1/2" and r.length.value == "12"
    assert [s.source for s in r.requirements] == ["rfq_line", "rfq_terms"]
    assert [d.field for d in r.discarded] == ["finish"]


@pytest.mark.parametrize("text,field,value,quote", [
    ("304 SS rd bar 1½\" dia x 12 ft - 5 ea", "diameter", "1½", "1½\" dia"),
    ("6061-T6 AL plate 48 x .25 x 96 - 3 ea", "unlabeled_dimensions", "0.25", ".25"),
    ("HRP&O 1011 sht 10ga 48\" x 96\" - 15 ea", "unlabeled_dimensions", "48", "48\""),
])
def test_as_written_values_pass(model, text, field, value, quote):
    replies, _ = model
    replies[text] = {field: [q(value, quote)] if field == "unlabeled_dimensions"
                     else q(value, quote)}
    r = interpret(item(text), Terms()).reading
    assert not r.discarded and kept(r)[0].value == value


def test_part_number_only_line(model):
    replies, _ = model
    text = "ACME-PN 88213 - 20 ea"
    replies[text] = {"customer_part_no": q("ACME-PN 88213", "ACME-PN 88213"),
                     "quantity": q("20", "20 ea", "ea")}
    r = interpret(item(text, "4"), TERMS).reading
    assert r.customer_part_no.value == "ACME-PN 88213" and r.quantity.value == "20"
    assert {f for f, v in r.model_dump(exclude_defaults=True).items()} == {
        "customer_part_no", "quantity"}


def test_model_failure_marks_the_line_and_others_continue(model):
    replies, _ = model
    replies["bad line"] = RuntimeError("gateway down")
    replies["ACME-PN 88213 - 20 ea"] = {"customer_part_no": q("ACME-PN 88213", "ACME-PN 88213")}
    bad, good = interpret_all([item("bad line", "1"), item("ACME-PN 88213 - 20 ea", "2")], TERMS)
    assert bad.reading is None
    assert [(i.kind, i.audience) for i in bad.issues] == [("model_failed", "internal")]
    assert good.reading.customer_part_no and not good.issues


def test_non_item_segments_are_skipped(model):
    _, sent = model
    req = item(DFARS, "-", kind="requirement")
    note = item("Delivery FOB our dock", "-", kind="note")
    assert interpret_all([req, note], TERMS) == [req, note]
    assert sent == []


def test_concurrent_lines_keep_order_and_terms_reach_the_model(model):
    replies, sent = model
    texts = [f"304 SS sheet 16ga 4x8 - {n} ea" for n in range(1, 7)]
    for t in texts:
        replies[t] = {"quantity": q(t.split(" - ")[1].split()[0], t.split(" - ")[1], "ea")}
    out = interpret_all([item(t, str(i)) for i, t in enumerate(texts)], TERMS)
    assert [l.reading.quantity.value for l in out] == [str(n) for n in range(1, 7)]
    assert len(sent) == 6 and all(DFARS in s for s in sent)
