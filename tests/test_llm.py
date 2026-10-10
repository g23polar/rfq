import pytest
from pydantic import BaseModel

from rfq import llm
from rfq.llm import MODEL_FAST, MODEL_READ, ModelCallError, call_json


class Reading(BaseModel):
    grade: str
    gauge: int


GOOD = '```json\n{"grade": "304", "gauge": 16}\n```'
BAD = '{"grade": "304", "gauge": "sixteen"}'


@pytest.fixture
def replies(monkeypatch):
    """Queue fake model replies; records every request that reaches the network function."""
    queue, sent = [], []

    def fake_send(model, messages, options):
        sent.append({"model": model, "messages": messages, "options": options})
        return queue.pop(0), 50, 20

    monkeypatch.setenv("NICRRON_API_KEY", "test-key")
    monkeypatch.setattr(llm, "_send", fake_send)
    return queue, sent


def test_valid_reply_in_a_code_fence_is_parsed(replies):
    queue, sent = replies
    queue.append(GOOD)
    result = call_json("Read the line.", "304 SS sheet 16ga", Reading)
    assert result.value == Reading(grade="304", gauge=16)
    assert len(result.calls) == 1 and result.calls[0].source == "live"
    assert result.calls[0].tokens_in == 50 and result.calls[0].tokens_out == 20
    assert '"gauge"' in sent[0]["messages"][0]["content"]  # the schema is in the prompt


def test_invalid_reply_gets_exactly_one_retry_with_the_error(replies):
    queue, sent = replies
    queue += [BAD, GOOD]
    result = call_json("Read the line.", "304 SS sheet 16ga", Reading)
    assert result.value.gauge == 16
    assert [c.attempt for c in result.calls] == [1, 2]
    retry = sent[1]["messages"]
    assert retry[-2] == {"role": "assistant", "content": BAD}
    assert "not valid" in retry[-1]["content"] and "gauge" in retry[-1]["content"]


def test_two_invalid_replies_raise_a_clear_error(replies):
    queue, sent = replies
    queue += [BAD, "I cannot help with that."]
    with pytest.raises(ModelCallError, match="after one retry") as raised:
        call_json("Read the line.", "304 SS sheet 16ga", Reading)
    assert len(sent) == 2 and len(raised.value.calls) == 2


def test_identical_request_is_served_from_the_cache(replies):
    queue, sent = replies
    queue.append(GOOD)
    first = call_json("Read the line.", "304 SS sheet 16ga", Reading)
    second = call_json("Read the line.", "304 SS sheet 16ga", Reading)
    assert len(sent) == 1
    assert second.calls[0].source == "cache" and second.value == first.value


def test_saved_responses_answer_calls_when_no_key_is_set(replies, monkeypatch):
    queue, sent = replies
    queue.append(GOOD)
    call_json("Read the line.", "304 SS sheet 16ga", Reading)  # records the response
    monkeypatch.delenv("NICRRON_API_KEY")
    assert call_json("Read the line.", "304 SS sheet 16ga", Reading).value.grade == "304"
    assert len(sent) == 1


def test_no_key_and_no_saved_response_fails_without_touching_the_network():
    with pytest.raises(ModelCallError, match="NICRRON_API_KEY is not set"):
        call_json("Read the line.", "a line never seen before", Reading)


def test_network_failure_becomes_a_model_call_error(monkeypatch):
    def boom(model, messages, options):
        raise TimeoutError("gateway timed out")

    monkeypatch.setenv("NICRRON_API_KEY", "test-key")
    monkeypatch.setattr(llm, "_send", boom)
    with pytest.raises(ModelCallError, match="gateway timed out"):
        call_json("Read the line.", "304 SS sheet 16ga", Reading)


def test_each_model_gets_only_the_options_it_accepts(replies):
    queue, sent = replies
    queue += [GOOD, GOOD]
    call_json("Read the line.", "x", Reading, model=MODEL_READ)
    call_json("Read the line.", "x", Reading, model=MODEL_FAST)
    assert "temperature" not in sent[0]["options"]
    assert sent[1]["options"] == {"temperature": 0}
