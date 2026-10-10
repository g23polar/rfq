"""Record one real run of the email fixture in PRISM and check the setup (plans/13).

Run: uv run python scripts/smoke_prism.py
Needs PRISMTRACE_API_KEY and PRISMTRACE_PROJECT_ID in .env; model calls come from the
local cache when present, so it costs nothing to rerun.
"""
import json
from pathlib import Path

from dotenv import load_dotenv

from rfq.intake import read_document, segment
from rfq.interpret import interpret
from rfq.prism import AGENT_NAME, Recorder, settings, setup_doctor
from rfq.safety import flag_lines, screen_document

load_dotenv(".env")
host, key, project = settings()
print(f"host {host}; key {'set' if key else 'MISSING'}; project {'set' if project else 'MISSING'}")
print("setup-doctor before:", json.dumps(setup_doctor())[:600])

path = Path("fixtures/rfq_email.txt")
rec = Recorder(rfq_id="SMOKE-" + path.stem, revision=1)
with rec.stage("intake.read", input=path.name) as s:
    doc = read_document(path.read_bytes(), path.name)
    s.output = {"kind": doc.source.kind, "stripped": [x.kind for x in doc.stripped]}
with rec.stage("safety", input=doc.cleaned) as s:
    screen = screen_document(doc)
    s.output = {"verdict": screen.verdict, "withheld": screen.passages}
with rec.stage("intake.segment", input=screen.masked) as s:
    result = segment(doc, withheld=screen.passages)
    flag_lines(result.lines, screen.withheld, doc.cleaned)
    s.output = result.terms
for line in result.lines:
    if line.segment.kind == "item":
        with rec.stage("interpret", line=line.buyer_line_no, input=line.segment.text) as s:
            s.output = interpret(line, result.terms).reading
rec.event("specialist.approve", input="smoke test", output={"approved_by": "smoke"})
rec.set_output({"lines": len(result.lines)})

payload = rec.ingest_payload(project or "")
print(f"trace {rec.trace_id}: {len(payload['spans'])} spans, "
      f"{len(rec.trace_payloads(project or ''))} model-call traces, agent {AGENT_NAME}")
print("sent:", rec.flush())
print("setup-doctor after:", json.dumps(setup_doctor())[:600])
