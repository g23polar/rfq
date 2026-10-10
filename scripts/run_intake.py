"""Run intake on a file and print what it found (plans/04-intake.md).

Run: uv run python scripts/run_intake.py fixtures/rfq_email.txt
Needs NICRRON_API_KEY in .env unless the response is already cached.
"""
import sys
from pathlib import Path

from dotenv import load_dotenv

from rfq.intake import read_document, segment

load_dotenv(".env")

for name in sys.argv[1:] or ["fixtures/rfq_email.txt", "fixtures/rfq.pdf"]:
    path = Path(name)
    doc = read_document(path.read_bytes(), path.name)
    result = segment(doc)
    print(f"== {path.name} ({doc.source.kind}); stripped: {[s.kind for s in doc.stripped]}")
    for key, value in result.terms.model_dump(exclude_none=True).items():
        if value:
            print(f"  {key}: {value}")
    for line in result.lines:
        s = line.segment
        print(f"  [{s.buyer_line_no:>2}] {s.kind:<11} p{s.location.page} "
              f"{s.location.start}-{s.location.end}  {s.text}"
              + "".join(f"  <{i.kind}>" for i in line.issues))
    if result.dropped:
        print(f"  dropped (not found in text): {result.dropped}")
    for c in result.calls:
        print(f"  call: {c.model} {c.source} {c.tokens_in}+{c.tokens_out} tokens {c.latency_ms} ms")
