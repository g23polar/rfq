"""Record the model responses the offline pipeline tests replay.

Run: uv run python scripts/record_fixtures.py
Makes live calls through Nicrron for any request not already saved in tests/recordings/.
Rerun it after changing a prompt. `--fresh` discards the saved responses first; avoid that
unless needed, because the saved PDF segmentation is a useful awkward case (it lists two
line-level standards as RFQ-wide requirements) that the pipeline tests rely on.
"""
import os
import shutil
import sys
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent
RECORDINGS = ROOT / "tests" / "recordings"

load_dotenv(ROOT / ".env")
if not os.environ.get("NICRRON_API_KEY"):
    sys.exit("NICRRON_API_KEY is not set in .env")
if "--fresh" in sys.argv:
    shutil.rmtree(RECORDINGS, ignore_errors=True)
os.environ["RFQ_LLM_CACHE"] = str(RECORDINGS)

from rfq import pipeline  # noqa: E402  (after the cache directory is set)

for name in ("rfq_email.txt", "rfq.pdf", "rfq_clean.pdf"):
    done = pipeline.process((ROOT / "fixtures" / name).read_bytes(), name, today=date(2026, 10, 10))
    print(f"{name}: {len(done.run.lines)} lines, {len(done.trace.calls)} calls, {done.run.counts}")
print(f"{len(list(RECORDINGS.glob('*.json')))} responses saved to {RECORDINGS}")
