import json
import urllib.request

import pytest
from pydantic import BaseModel

from rfq import llm, prism
from rfq.llm import call_json
from rfq.prism import AGENT_NAME, Recorder

KEY, PROJECT = "pt-sk-test-secret", "11111111-2222-3333-4444-555555555555"


class Answer(BaseModel):
    ok: bool


@pytest.fixture
def sent(monkeypatch):
    """Capture what would be posted to PRISM; the model answers from a fake."""
    posts = []
    monkeypatch.setenv("PRISMTRACE_API_KEY", KEY)
    monkeypatch.setenv("PRISMTRACE_PROJECT_ID", PROJECT)
    monkeypatch.setattr(prism, "_post", lambda host, key, path, payload:
                        posts.append((path, payload)) or True)
    monkeypatch.setenv("NICRRON_API_KEY", "test-key")
    monkeypatch.setattr(llm, "_send", lambda model, messages, options: ('{"ok": true}', 30, 5))
    return posts


def recorded_run() -> Recorder:
    rec = Recorder("RFQ-1", revision=2, started="2026-10-10T12:00:00+00:00")
    with rec.stage("safety", input="raw text") as s:
        s.output = {"verdict": "clean"}
    with rec.stage("interpret", line="10", input="304 SS sheet 16ga 4x8 - 10 ea") as s:
        call_json("Read the line.", "304 SS sheet", Answer)
        s.output = Answer(ok=True)
    with pytest.raises(ValueError):
        with rec.stage("price", line="10"):
            raise ValueError("no benchmark")
    rec.event("specialist.approve", input="looks right", output={"approved_by": "dana"})
    return rec


def test_one_trace_with_nested_stages_and_model_calls(sent):
    rec = recorded_run()
    assert rec.flush() is True
    (path, ingest), *traces = sent
    assert path == "/api/spans/ingest" and ingest["trace_id"] == rec.trace_id
    spans = {s["name"]: s for s in ingest["spans"]}
    root = spans["rfq RFQ-1 rev 2"]
    assert root["parent_span_id"] is None and root["span_type"] == "agent"
    for name in ("safety", "interpret line 10", "price line 10", "specialist.approve"):
        assert spans[name]["parent_span_id"] == root["span_id"]
    llm_span = spans["interpret model call"]
    assert llm_span["parent_span_id"] == spans["interpret line 10"]["span_id"]
    assert llm_span["span_type"] == "llm" and llm_span["token_count_input"] == 30
    assert spans["price line 10"]["status"] == "error"
    assert "no benchmark" in spans["price line 10"]["error_message"]
    assert all(s["metadata"]["agent_name"] == AGENT_NAME for s in ingest["spans"])

    assert [p for p, _ in traces] == ["/api/trajectories", "/api/traces"]
    trajectory = traces[0][1]
    assert trajectory["request_id"] == rec.trace_id and trajectory["agent_name"] == AGENT_NAME
    assert [st["label"] for st in trajectory["steps"]][:4] == [
        "safety", "interpret line 10", f"interpret line 10: {llm.MODEL_READ} (live)",
        "price line 10"]
    assert trajectory["steps"][3]["status"] == "error"
    assert trajectory["steps"][-1]["step_type"] == "final_answer"
    trace = traces[1][1]
    assert trace["agent_name"] == AGENT_NAME and trace["session_id"] == rec.trace_id
    assert trace["metadata"]["line"] == "10" and trace["output_message"] == '{"ok": true}'


def test_the_key_is_never_in_a_payload(sent):
    recorded_run().flush()
    assert all(KEY not in json.dumps(payload) for _, payload in sent)


def test_same_revision_and_start_give_the_same_trace_id():
    a = Recorder("RFQ-1", 1, started="t0")
    assert a.trace_id == Recorder("RFQ-1", 1, started="t0").trace_id
    assert a.trace_id != Recorder("RFQ-1", 2, started="t0").trace_id


def test_no_key_sends_nothing(monkeypatch):
    monkeypatch.delenv("PRISMTRACE_API_KEY", raising=False)
    monkeypatch.setattr(prism, "_post", lambda *a: pytest.fail("must not send"))
    rec = Recorder("RFQ-1")
    with rec.stage("safety"):
        pass
    assert rec.flush() is False


def test_a_recording_failure_never_raises(monkeypatch):
    monkeypatch.setenv("PRISMTRACE_API_KEY", KEY)
    monkeypatch.setenv("PRISMTRACE_PROJECT_ID", PROJECT)

    def down(*args, **kwargs):
        raise OSError("connection refused")

    monkeypatch.setattr(urllib.request, "urlopen", down)
    rec = Recorder("RFQ-1")
    with rec.stage("safety"):
        pass
    assert rec.flush() is False


def test_capture_sees_calls_from_interpret_all_threads(sent):
    from rfq.interpret import interpret_all
    from rfq.models import Line, Segment, Terms

    lines = [Line(buyer_line_no=n, segment=Segment(buyer_line_no=n, text="304 SS sheet"))
             for n in ("1", "2", "3")]
    with llm.capture() as calls:
        interpret_all(lines, Terms())
    assert len(calls) == 3


def test_record_run_labels_every_stage_and_line_of_a_pipeline_run(sent, monkeypatch):
    from datetime import date
    from pathlib import Path

    from rfq import pipeline

    root = Path(__file__).parent.parent
    monkeypatch.setenv("RFQ_LLM_CACHE", str(root / "tests" / "recordings"))
    monkeypatch.delenv("NICRRON_API_KEY", raising=False)
    done = pipeline.process((root / "fixtures" / "rfq_email.txt").read_bytes(), "rfq_email.txt",
                            today=date(2026, 10, 10), recorder=prism.record_run)

    (_, ingest), (_, trajectory), *traces = sent
    assert done.run.prism_trace_id == ingest["trace_id"]
    names = [s["name"] for s in ingest["spans"]]
    for stage in ("safety.screen", "intake.segment", "interpret", "interpret line 1",
                  "interpret line 6", "standardize line 1", "decide line 6"):
        assert stage in names, stage
    assert "model" not in names  # every model call was matched to its stage
    assert len(traces) == len(done.trace.calls)
    assert {t["metadata"]["stage"] for _, t in traces} >= {"safety.screen", "intake.segment",
                                                        "interpret"}
    labels = [st["label"] for st in trajectory["steps"]]
    assert labels[0] == "intake.read" and labels[-1].startswith("rfq Q-")


def test_record_run_grounds_assumptions_in_the_knowledge_base(sent, monkeypatch):
    from rfq.models import Line, Run, RunSource, Segment, issue

    searched = []
    monkeypatch.setattr(prism, "kb_search", lambda q, limit=1: searched.append(q) or
                        [{"content": "16 gauge stainless steel sheet is 0.0625 in thick.",
                          "doc_id": "d1", "id": "c1"}])
    line = Line(buyer_line_no="1", segment=Segment(buyer_line_no="1", text="304 SS sheet 16ga"),
                issues=[issue("assumption", "16 ga stainless read as 0.0625 in."),
                        issue("missing", "Quantity not stated.")])
    run = Run(rfq_id="Q-1", created="2026-10-10T15:00:00+00:00",
              source=RunSource(kind="text"), lines=[line])
    prism.record_run(run, pipeline_trace())
    assert searched == ["16 ga stainless read as 0.0625 in."]
    span = next(s for s in sent[0][1]["spans"] if s["name"] == "grounding line 1")
    assert span["span_type"] == "retrieval" and "0.0625 in thick" in span["output_text"]


def pipeline_trace():
    from rfq.pipeline import Trace
    return Trace()
