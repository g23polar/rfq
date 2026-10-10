"""Run the safety screen on a file and print what it withheld (plans/05-safety-screen.md).

Run: uv run python scripts/run_safety.py fixtures/rfq.pdf
Needs NICRRON_API_KEY in .env unless the response is already cached.
"""
import sys
from pathlib import Path

from dotenv import load_dotenv

from rfq.intake import read_document
from rfq.safety import screen_document

load_dotenv(".env")

for name in sys.argv[1:] or ["fixtures/rfq.pdf", "fixtures/rfq_email.txt"]:
    path = Path(name)
    doc = read_document(path.read_bytes(), path.name)
    result = screen_document(doc)
    print(f"== {path.name} ({doc.source.kind}): {result.verdict}")
    for w in result.withheld:
        loc = w.location
        print(f"  withheld [{w.detector}] p{loc.page} {loc.start}-{loc.end}: {w.text!r}"
              f"  ({w.reason})")
    if result.dropped:
        print(f"  dropped (not found in text): {result.dropped}")
    if result.model_error:
        print(f"  model failed, patterns only: {result.model_error}")
    for c in result.calls:
        print(f"  call: {c.model} {c.source} {c.tokens_in}+{c.tokens_out} tokens {c.latency_ms} ms"
              f"  output: {c.output.strip()[:300]!r}")
