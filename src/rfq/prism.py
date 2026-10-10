"""PRISM recording over HTTP (plans/13-prism-recording.md).

One trace per RFQ run: a root span for the run, a child span per stage (per line where the
stage works on lines), and an `llm` span under the stage for each model call. Model calls
are also sent to `/api/traces`, the only place PRISM takes an `agent_name`, sharing the
run's session. The same run is sent to `/api/trajectories` as labeled steps (one per stage,
one per model call): that is what the dashboard's "Agent Run" panel shows; without it PRISM
builds the panel from the model calls alone and the stage names are lost. Everything is buffered and sent by `flush()` after the run, so recording
never slows a quote; a failure is logged and never raised. With no key set, nothing is sent.

    rec = Recorder(rfq_id="RFQ-2026-1147", revision=1)
    with rec.stage("interpret", line="1", input=segment.text) as s:
        line = interpret(line, terms)
        s.output = line.reading
    rec.flush()                  # model calls made inside a stage are recorded under it

The pipeline (task 14) records after the fact instead: `record_run(run, trace)` replays its
stage list and model calls, matching each call to its stage by the stage's prompt.

Span shapes follow the prismtrace SDK's `/api/spans/ingest` payload (span_type is one of
chain, llm, tool, retrieval, agent; times are ISO 8601 in UTC).
"""
import json
import logging
import os
import threading
import urllib.error
import urllib.request
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Iterator

from pydantic import BaseModel

from rfq.llm import CallRecord, capture

log = logging.getLogger(__name__)

AGENT_NAME = "rfq-to-quote"
AGENT_ID = AGENT_NAME  # one identity: PRISM makes a separate agent per distinct id
DEFAULT_HOST = "https://prism.blockconvey.com"
MAX_TEXT = 10000  # the SDK truncates span text to this
TIMEOUT_S = 15
_NAMESPACE = uuid.UUID("8f9c1b52-3a64-4c3e-9a51-6d2f0e7b4a10")  # for deterministic ids


def settings() -> tuple[str, str | None, str | None]:
    return (os.environ.get("PRISMTRACE_HOST") or DEFAULT_HOST).rstrip("/"), \
        os.environ.get("PRISMTRACE_API_KEY"), os.environ.get("PRISMTRACE_PROJECT_ID")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _text(value: Any) -> str | None:
    """Stage input or output as text: models as JSON, everything else as str."""
    if value is None:
        return None
    if isinstance(value, BaseModel):
        text = value.model_dump_json(exclude_none=True)
    elif isinstance(value, (list, tuple)) and value and all(isinstance(v, BaseModel) for v in value):
        text = "[" + ",".join(v.model_dump_json(exclude_none=True) for v in value) + "]"
    elif isinstance(value, (dict, list, tuple)):
        text = json.dumps(value, default=str)
    else:
        text = str(value)
    return text[:MAX_TEXT]


@dataclass
class Span:
    """A stage while it runs. Set `output`, `calls` or `error` inside the `with` block."""

    name: str
    span_id: str
    parent_span_id: str | None
    span_type: str
    input: Any = None
    output: Any = None
    calls: list[CallRecord] = field(default_factory=list)
    error: str | None = None
    metadata: dict = field(default_factory=dict)
    start: datetime = field(default_factory=_now)
    end: datetime | None = None


class Recorder:
    """Buffers one run's spans and model calls, then sends them in `flush()`."""

    def __init__(self, rfq_id: str, revision: int = 1, started: str | None = None):
        self.rfq_id, self.revision = rfq_id, revision
        started = started or _now().isoformat()
        # One trace per RFQ revision; the start time keeps demo reruns apart.
        self.trace_id = str(uuid.uuid5(_NAMESPACE, f"{rfq_id}:{revision}:{started}"))
        self.session_id = self.trace_id
        self.root = Span(name=f"rfq {rfq_id} rev {revision}", span_id=self._id("root"),
                         parent_span_id=None, span_type="agent",
                         metadata={"rfq_id": rfq_id, "revision": revision})
        self.spans: list[Span] = []
        self._count = 0
        self._lock = threading.Lock()  # stages may run on several threads

    def _id(self, *parts: Any) -> str:
        return str(uuid.uuid5(_NAMESPACE, ":".join([self.trace_id, *map(str, parts)])))

    @contextmanager
    def stage(self, name: str, input: Any = None, line: str | None = None,
              span_type: str = "chain", parent: Span | None = None) -> Iterator[Span]:
        """Time one stage and collect the model calls made inside it. An exception is
        recorded on the span and re-raised."""
        with self._lock:
            self._count += 1
            n = self._count
        span = Span(name=f"{name} line {line}" if line else name,
                    span_id=self._id(name, line, n),
                    parent_span_id=(parent or self.root).span_id, span_type=span_type,
                    input=input, metadata={"stage": name, **({"line": line} if line else {})})
        try:
            with capture() as calls:
                yield span
        except Exception as e:
            span.error = f"{type(e).__name__}: {e}"
            raise
        finally:
            span.calls = span.calls or calls
            span.end = _now()
            with self._lock:
                self.spans.append(span)

    def add(self, name: str, start: datetime, duration_ms: int, input: Any = None,
            output: Any = None, line: str | None = None, error: str | None = None,
            calls: list[CallRecord] | None = None, parent: Span | None = None) -> Span:
        """Record a stage that has already run."""
        with self._lock:
            self._count += 1
            n = self._count
        span = Span(name=f"{name} line {line}" if line else name, span_id=self._id(name, line, n),
                    parent_span_id=(parent or self.root).span_id, span_type="chain",
                    input=input, output=output, calls=list(calls or []), error=error,
                    metadata={"stage": name, **({"line": line} if line else {})},
                    start=start, end=start + timedelta(milliseconds=duration_ms))
        with self._lock:
            self.spans.append(span)
        return span

    def event(self, name: str, input: Any = None, output: Any = None, **metadata: Any) -> None:
        """Record something that happened outside a stage: approval, an edit, a send."""
        with self.stage(name, input=input, span_type="tool") as s:
            s.output = output
            s.metadata.update(metadata)

    def set_output(self, output: Any) -> None:
        """The run's final result, shown on the root span."""
        self.root.output = output

    # --- Payloads -------------------------------------------------------------------

    def _span_json(self, s: Span) -> dict:
        end = s.end or _now()
        return {
            "span_id": s.span_id, "parent_span_id": s.parent_span_id, "name": s.name,
            "span_type": s.span_type, "input_text": _text(s.input), "output_text": _text(s.output),
            "metadata": {"agent_name": AGENT_NAME, **s.metadata},
            "start_time": s.start.isoformat(), "end_time": end.isoformat(),
            "duration_ms": round((end - s.start).total_seconds() * 1000, 1),
            "status": "error" if s.error else "ok", "error_message": s.error,
        }

    def _llm_spans(self, s: Span) -> list[dict]:
        """One `llm` child span per model call, laid end to end inside the stage."""
        out, at = [], s.start
        for i, c in enumerate(s.calls):
            end = at + timedelta(milliseconds=c.latency_ms)
            out.append({
                "span_id": self._id(s.span_id, "llm", i), "parent_span_id": s.span_id,
                "name": f"{s.metadata.get('stage', s.name)} model call", "span_type": "llm",
                "input_text": _text(c.messages), "output_text": _text(c.output),
                "metadata": {"agent_name": AGENT_NAME, "attempt": c.attempt, "source": c.source},
                "start_time": at.isoformat(), "end_time": end.isoformat(),
                "duration_ms": c.latency_ms, "status": "ok", "error_message": None,
                "token_count_input": c.tokens_in, "token_count_output": c.tokens_out,
                "model": c.model,
            })
            at = end
        return out

    def ingest_payload(self, project_id: str) -> dict:
        self.root.end = self.root.end or _now()
        spans = [self._span_json(self.root)]
        for s in self.spans:
            spans.append(self._span_json(s))
            spans += self._llm_spans(s)
        return {"trace_id": self.trace_id, "project_id": project_id,
                "session_id": self.session_id,
                "metadata": {"source": "rfq-http", "agent_name": AGENT_NAME,
                             "rfq_id": self.rfq_id, "revision": self.revision},
                "spans": spans}

    def trace_payloads(self, project_id: str) -> list[dict]:
        """Each model call as a PRISM trace, carrying the agent name."""
        out = []
        for s in self.spans:
            for i, c in enumerate(s.calls):
                out.append({
                    "project_id": project_id, "trace_id": self._id(s.span_id, "trace", i),
                    "session_id": self.session_id, "agent_id": AGENT_ID, "agent_name": AGENT_NAME,
                    "model": c.model, "input_messages": c.messages, "output_message": c.output,
                    "latency_ms": c.latency_ms, "token_count_input": c.tokens_in,
                    "token_count_output": c.tokens_out,
                    "metadata": {"rfq_id": self.rfq_id, "revision": self.revision,
                                 **s.metadata, "attempt": c.attempt, "source": c.source},
                })
        return out

    def trajectory_payload(self, project_id: str) -> dict:
        """The run as ordered, labeled steps: each stage, then the model calls it made."""
        steps = []
        for s in sorted(self.spans, key=lambda s: s.start):
            end = s.end or _now()
            steps.append({
                "step_type": "tool_call", "label": s.name, "tool_name": s.metadata.get("stage", s.name),
                "input_summary": (_text(s.input) or "")[:200],
                "output_summary": (s.error or _text(s.output) or "")[:200],
                "duration_ms": int((end - s.start).total_seconds() * 1000),
                "token_count": sum(c.tokens_in + c.tokens_out for c in s.calls),
                "status": "error" if s.error else "success",
            })
            for c in s.calls:
                steps.append({
                    "step_type": "reasoning", "label": f"{s.name}: {c.model} ({c.source})",
                    "input_summary": (c.messages[-1]["content"] if c.messages else "")[:200],
                    "output_summary": c.output[:200], "duration_ms": c.latency_ms,
                    "token_count": c.tokens_in + c.tokens_out, "status": "success",
                })
        steps.append({"step_type": "final_answer", "label": self.root.name,
                      "output_summary": (_text(self.root.output) or "")[:200],
                      "duration_ms": 0, "token_count": 0,
                      "status": "error" if any(s.error for s in self.spans) else "success"})
        models = [c.model for s in self.spans for c in s.calls]
        return {"project_id": project_id, "conversation_id": self.session_id,
                "request_id": self.trace_id, "agent_id": AGENT_ID, "agent_name": AGENT_NAME,
                "steps": steps, "total_duration_ms": sum(st["duration_ms"] for st in steps),
                "final_status": steps[-1]["status"],
                "model": max(set(models), key=models.count) if models else None}

    def flush(self) -> bool:
        """Send everything. Returns whether all of it was accepted; never raises."""
        host, key, project = settings()
        if not key or not project:
            log.info("PRISM key or project not set; run %s not recorded", self.trace_id)
            return False
        ok = _post(host, key, "/api/spans/ingest", self.ingest_payload(project))
        ok = _post(host, key, "/api/trajectories", self.trajectory_payload(project)) and ok
        for payload in self.trace_payloads(project):
            ok = _post(host, key, "/api/traces", payload) and ok
        return ok


def _stage_prompts() -> dict[str, str]:
    """Each model-calling stage's system prompt, to tell its calls apart."""
    from rfq import intake, interpret, questions, safety
    return {safety.SYSTEM: "safety.screen", intake.SYSTEM: "intake.segment",
            interpret.SYSTEM: "interpret", questions.SYSTEM: "questions.reword"}


def record_run(run, trace) -> str | None:
    """Send a finished pipeline run (`rfq.pipeline.process`) to PRISM. Returns the PRISM
    trace id, or None when nothing was recorded. Plugged in by `rfq.app`."""
    rec = Recorder(run.rfq_id, run.revision, started=run.created)
    prompts = _stage_prompts()
    by_stage: dict[str, list[CallRecord]] = {}
    for call in trace.calls:
        system = call.messages[0]["content"] if call.messages else ""
        stage = next((name for prompt, name in prompts.items() if system.startswith(prompt)),
                     "model")
        by_stage.setdefault(stage, []).append(call)
    line_of = {l.segment.text: l.buyer_line_no for l in run.lines}

    for s in trace.spans:
        start = datetime.fromisoformat(s.started).astimezone(timezone.utc)
        error = s.output if s.status == "error" else None
        calls = by_stage.pop(s.name, []) if s.line_no is None else []
        if s.name == "interpret":
            # One span for the batch; each line's call goes in its own child span.
            parent = rec.add(s.name, start, s.duration_ms, input=s.input, output=s.output,
                             error=error)
            for c in calls:
                text = c.messages[-1]["content"].split("<line>\n", 1)[-1].split("\n</line>")[0]
                rec.add("interpret", start, c.latency_ms, input=text, output=c.output,
                        line=line_of.get(text), calls=[c], parent=parent)
        else:
            rec.add(s.name, start, s.duration_ms, input=s.input, output=s.output,
                    line=s.line_no, error=error, calls=calls)
    for leftover in by_stage.values():  # calls whose stage could not be told
        rec.add("model", rec.root.start, 0, calls=leftover)

    if rec.spans:
        rec.root.start = min(sp.start for sp in rec.spans)
        rec.root.end = max(sp.end for sp in rec.spans if sp.end)
    rec.root.input = run.source.filename or run.source.kind
    rec.set_output({"quote_status": run.quote_status, "counts": run.counts, "total": run.total,
                    "completeness": run.completeness,
                    "leak_check": run.leak_check.passed if run.leak_check else None})
    return rec.trace_id if rec.flush() else None


def _post(host: str, key: str, path: str, payload: dict) -> bool:
    """The only function that sends to PRISM."""
    request = urllib.request.Request(
        host + path, data=json.dumps(payload, default=str).encode(), method="POST",
        headers={"Content-Type": "application/json", "X-PRISMtrace-Key": key})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:
            return 200 <= response.status < 300
    except urllib.error.HTTPError as e:
        log.warning("PRISM %s failed: HTTP %s %s", path, e.code, e.read()[:300])
    except Exception as e:  # recording must never fail a quote
        log.warning("PRISM %s failed: %s", path, e)
    return False


def setup_doctor() -> dict:
    """PRISM's own health check for the project (`GET /api/setup-doctor`)."""
    host, key, project = settings()
    if not key or not project:
        return {"error": "PRISMTRACE_API_KEY or PRISMTRACE_PROJECT_ID is not set"}
    request = urllib.request.Request(f"{host}/api/setup-doctor?project_id={project}",
                                     headers={"X-PRISMtrace-Key": key})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}", "body": e.read()[:500].decode(errors="replace")}
    except Exception as e:
        return {"error": str(e)}
