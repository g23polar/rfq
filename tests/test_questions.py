import json

import pytest

from rfq import llm
from rfq.models import Question
from rfq.questions import check_rewording, reword, supplier_names

TEMPLATE = Question(
    text="Line 40: Length \"12\" has no unit. Please provide the missing detail. "
         "Options: 12 inches, 12 feet.",
    options=["12 inches", "12 feet"])
GOOD = "For line 40, is the bar length 12 inches or 12 feet? Length \"12\" has no unit."


@pytest.fixture
def model(monkeypatch):
    """Queue fake replies for the wording model."""
    queue, sent = [], []

    def fake_send(model, messages, options):
        sent.append({"model": model, "messages": messages})
        reply = queue.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return json.dumps({"text": reply}), 10, 10

    monkeypatch.setenv("NICRRON_API_KEY", "test-key")
    monkeypatch.setattr(llm, "_send", fake_send)
    return queue, sent


def test_good_rewording_replaces_the_text_and_keeps_options(model):
    queue, sent = model
    queue.append(GOOD)
    out = reword(TEMPLATE)
    assert out.text == GOOD and out.options == TEMPLATE.options and out.blocking
    assert sent[0]["model"] == llm.MODEL_FAST
    assert "12 inches; 12 feet" in sent[0]["messages"][1]["content"]


@pytest.mark.parametrize("bad", [
    "For line 40, is the length 12 inches or 12 feet? We can do it for $4.50 a foot.",
    "Line 40: is the length 12 inches or 12 feet? Our price is 25 per piece.",
    "Line 40: 12 inches or 12 feet? We need this by October 14.",
    "Line 40: 12 inches or 12 feet? We will quote right away.",
    "Line 40: 12 inches or 12 feet? We guarantee the best price.",
    "Line 40: 12 inches or 12 feet? I promise a fast answer.",
    "Line 40: 12 inches or 12 feet? It affects our cost.",
    "Line 40: 12 inches or 12 feet? Our margin depends on it.",
    "Line 40: 12 inches or 12 feet? Our supplier needs to know.",
    "Line 40: 12 inches or 12 feet? The floor price matters.",
    "Line 40: 12 inches or 12 feet? Prices in dollars.",
    "",
])
def test_rejected_rewording_returns_the_template_unchanged(model, bad):
    queue, _ = model
    queue.append(bad)
    assert reword(TEMPLATE) == TEMPLATE


def test_supplier_name_is_rejected(model):
    queue, _ = model
    name = supplier_names()[0]
    queue.append(f"Line 40: 12 inches or 12 feet? We buy from {name}.")
    assert reword(TEMPLATE) == TEMPLATE


def test_model_failure_returns_the_template(model):
    queue, _ = model
    queue.append(TimeoutError("down"))
    assert reword(TEMPLATE) == TEMPLATE


def test_no_key_and_no_cache_returns_the_template(monkeypatch):
    assert reword(TEMPLATE) == TEMPLATE


def test_invalid_json_twice_returns_the_template(monkeypatch):
    monkeypatch.setenv("NICRRON_API_KEY", "k")
    monkeypatch.setattr(llm, "_send", lambda m, msgs, o: ("not json", 1, 1))
    assert reword(TEMPLATE) == TEMPLATE


def test_check_accepts_numbers_that_the_template_has_in_other_formats():
    assert check_rewording("Line 40: 12.0 inches?", "Line 40: is it 12 inches?") == []
    assert check_rewording("Line 1: 1,000 ft?", "Line 1: is it 1000 ft?") == []


def test_check_flags_each_problem():
    assert check_rewording("Line 4: ok?", "Line 5: ok?")
    assert check_rewording("Line 4: ok?", "Line 4: ok? Costs vary.")
    assert check_rewording("Line 4: ok?", "Line 4: ok? In October?")
    assert check_rewording("Line 4: ok?", "Line 4: could you confirm?") == []
    assert check_rewording("Line 4: October delivery?", "Line 4: October delivery ok?") == []
