"""Run every stage for one RFQ and assemble the draft (plans/14-pipeline-and-api.md).

`process` returns the Run plus a Trace of what each stage did and every model call made, which
is what PRISM recording (task 13) sends. A recorder, if given, is called once at the end and a
failure in it never fails the run.
"""

import hashlib
import json
import logging
import time
from collections import Counter
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import date, datetime

from pydantic import BaseModel, Field

from rfq import (availability, compliance, decide, intake, interpret, llm, match, price,
                 questions, render, safety, standardize, verify)
from rfq.context import Context
from rfq.llm import CallRecord
from rfq.models import Line, Run, Terms, buyer_view, issue
from rfq.reference import ReferenceData, load_reference

log = logging.getLogger(__name__)

# The rule stages, in the order context.py lists them.
RULE_STAGES = (
    ("standardize", standardize.standardize, lambda l: l.spec),
    ("resolve", match.resolve, lambda l: [o.candidate for o in l.offers]),
    ("availability", availability.check, lambda l: [o.availability for o in l.offers]),
    ("price", price.price, lambda l: [o.price for o in l.offers]),
    ("compliance", compliance.check, lambda l: [o.compliance for o in l.offers]),
    ("decide", decide.decide, lambda l: {"status": l.status, "question": l.question,
                                         "review_note": l.review_note}),
    ("verify", verify.verify, lambda l: {"status": l.status, "verification": l.verification}),
)
OPEN_STATUSES = ("needs_buyer_input", "needs_specialist_review")


class Span(BaseModel):
    """One stage's work, for the run record."""

    name: str
    line_no: str | None = None  # None for document-level stages
    input: str = ""
    output: str = ""
    started: str
    duration_ms: int
    status: str = "ok"


class Trace(BaseModel):
    spans: list[Span] = Field(default_factory=list)
    calls: list[CallRecord] = Field(default_factory=list)


Recorder = Callable[[Run, Trace], str | None]  # returns the PRISM trace id, if it has one


@dataclass
class Processed:
    run: Run
    trace: Trace


def _dump(value) -> str:
    def plain(v):
        if isinstance(v, BaseModel):
            return v.model_dump(exclude_none=True, exclude_defaults=True)
        if isinstance(v, (list, tuple)):
            return [plain(x) for x in v]
        if isinstance(v, dict):
            return {k: plain(x) for k, x in v.items()}
        return v
    return json.dumps(plain(value), default=str)


class _Clock:
    """Times a stage and appends its span."""

    def __init__(self, trace: Trace, name: str, line_no: str | None = None, input: str = ""):
        self.trace, self.name, self.line_no, self.input = trace, name, line_no, input
        self.output, self.status = "", "ok"

    def __enter__(self):
        self.started, self.t0 = datetime.now().astimezone().isoformat(), time.monotonic()
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc is not None:
            self.status, self.output = "error", str(exc)
        self.trace.spans.append(Span(
            name=self.name, line_no=self.line_no, input=self.input, output=self.output,
            started=self.started, duration_ms=int((time.monotonic() - self.t0) * 1000),
            status=self.status))
        return False


def _rule_stages(line: Line, ctx: Context, trace: Trace) -> Line:
    """Stages 4 to 10 for one line. A stage that crashes sends the line to specialist review
    and the rest of the quote carries on (NF-6)."""
    for name, stage, shows in RULE_STAGES:
        try:
            with _Clock(trace, name, line.buyer_line_no, line.segment.text) as span:
                line = stage(line, ctx)
                span.output = _dump(shows(line))
        except Exception as e:
            log.exception("stage %s failed on line %s", name, line.buyer_line_no)
            line.issues.append(issue("model_failed", f"The {name} step failed: {e}"))
            return decide.decide(line, ctx)
    # An offer that meets the line's requirements is listed ahead of one that doesn't.
    line.offers.sort(key=lambda o: any(c.result == "not_met" for c in o.compliance))
    return line


def _squash(text: str) -> str:
    return " ".join(text.split()).lower()


def _keep_rfq_wide(terms: Terms, lines: list[Line], text: str) -> list[str]:
    """Drop RFQ-wide requirements whose wording appears only inside item lines.

    Segmentation sometimes lifts a standard written on one line ("ASTM A36") into the
    RFQ-wide list, which would then be demanded of every line. A requirement is RFQ-wide only
    if its words appear somewhere outside the item lines. Returns what was dropped."""
    outside = list(text)
    for line in lines:
        loc = line.segment.location
        if line.segment.kind == "item" and loc.start is not None and loc.end is not None:
            outside[loc.start:loc.end] = " " * (loc.end - loc.start)
    remainder = _squash("".join(outside))
    kept, dropped = [], []
    for req in terms.requirements:
        wording = _squash(req.source_text or str(req.value))
        (kept if wording in remainder else dropped).append(req)
    terms.requirements = kept
    return [str(r.source_text or r.value) for r in dropped]


def finish(run: Run) -> Run:
    """Counts, total, completeness, the buyer email and the leak check, from the lines."""
    run.counts = dict(Counter(l.status for l in run.lines if l.status))
    run.total = buyer_view(run).total
    run.completeness = ("partial" if any(l.status in OPEN_STATUSES for l in run.lines)
                        else "complete")
    run.email = render.email_text(run)
    run.leak_check = verify.leak_check(
        run, [render.visible_text(render.quote_html(run)), run.email])
    return run


def process(data: bytes | str, filename: str | None = None, today: date | None = None,
            ref: ReferenceData | None = None, recorder: Recorder | None = None) -> Processed:
    today = today or date.today()
    ref = ref or load_reference()
    trace = Trace()
    with llm.watching(trace.calls):
        with _Clock(trace, "intake.read", input=filename or "pasted text") as span:
            doc = intake.read_document(data, filename)
            span.output = f"{doc.source.kind}, {len(doc.cleaned)} characters, " \
                          f"{len(doc.stripped)} passages stripped by rule"
        with _Clock(trace, "safety.screen", input=doc.cleaned) as span:
            screen = safety.screen_document(doc)
            span.output = _dump({"verdict": screen.verdict, "withheld": screen.withheld})

        lines: list[Line] = []
        terms = None
        if screen.verdict != "blocked":
            with _Clock(trace, "intake.segment", input=screen.masked) as span:
                taken = intake.segment(doc, withheld=screen.passages)
                span.output = _dump({"terms": taken.terms,
                                     "lines": [l.segment for l in taken.lines]})
            terms, lines = taken.terms, taken.lines
            dropped = _keep_rfq_wide(terms, lines, doc.cleaned)
            if dropped:
                span.output += f" | not RFQ-wide, dropped: {dropped}"
            safety.flag_lines(lines, screen.withheld, doc.cleaned)
            with _Clock(trace, "interpret", input=f"{len(lines)} lines") as span:
                lines = interpret.interpret_all(lines, terms)
                span.output = _dump([l.reading for l in lines])
            ctx = Context(terms=terms, ref=ref, today=today)
            lines = [_rule_stages(line, ctx, trace) for line in lines]
            with _Clock(trace, "questions.reword") as span:
                asking = [l for l in lines if l.question]
                with ThreadPoolExecutor(max_workers=8) as pool:
                    for line, q in zip(asking, pool.map(questions.reword,
                                                        [l.question for l in asking])):
                        line.question = q
                span.output = _dump([l.question for l in asking])

    digest = hashlib.sha1(doc.original.encode()).hexdigest()[:6].upper()
    run = Run(rfq_id=f"Q-{today:%y%m%d}-{digest}",
              created=datetime.now().astimezone().isoformat(timespec="seconds"),
              source=doc.source, withheld=screen.withheld, lines=lines)
    if terms is not None:
        run.terms = terms
    finish(run)
    if recorder:
        try:
            run.prism_trace_id = recorder(run, trace)
        except Exception:
            log.exception("recording run %s failed", run.rfq_id)
    return Processed(run=run, trace=trace)
