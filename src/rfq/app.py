"""The API and review screen host (plans/14-pipeline-and-api.md).

Run: uv run uvicorn rfq.app:app --reload
Runs are kept in memory; restarting the server forgets them.
"""

from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, PlainTextResponse
from pydantic import BaseModel

from rfq import pipeline, render
from rfq.models import Run

load_dotenv(".env")

ROOT = Path(__file__).parent
FIXTURES = ROOT.parent.parent / "fixtures"
SAMPLES = {"email": "rfq_email.txt", "pdf": "rfq.pdf"}

app = FastAPI(title="RFQ-to-Quote Agent")
RUNS: dict[str, pipeline.Processed] = {}


def _recorder() -> pipeline.Recorder | None:
    """PRISM recording (task 13) plugs in here: `rfq.prism.record_run(run, trace) -> trace id`."""
    try:
        from rfq import prism
    except ImportError:
        return None
    return getattr(prism, "record_run", None)


def _process(data: bytes | str, filename: str | None) -> Run:
    done = pipeline.process(data, filename, recorder=_recorder())
    RUNS[done.run.rfq_id] = done
    return done.run


def _run(rfq_id: str) -> Run:
    if rfq_id not in RUNS:
        raise HTTPException(404, f"No run {rfq_id}. Runs are lost when the server restarts.")
    return RUNS[rfq_id].run


@app.post("/api/rfq")
async def create_rfq(file: UploadFile | None = File(None), text: str | None = Form(None)) -> Run:
    """Process an uploaded file (email text or PDF) or pasted text into a draft quote."""
    if file is not None:
        return _process(await file.read(), file.filename)
    if text and text.strip():
        return _process(text, None)
    raise HTTPException(400, "Send a file or some text.")


@app.get("/api/samples")
def samples() -> dict[str, str]:
    return SAMPLES


@app.post("/api/samples/{name}")
def run_sample(name: str) -> Run:
    if name not in SAMPLES:
        raise HTTPException(404, f"No sample {name}.")
    path = FIXTURES / SAMPLES[name]
    return _process(path.read_bytes(), path.name)


@app.get("/api/rfq/{rfq_id}")
def get_rfq(rfq_id: str) -> Run:
    run = _run(rfq_id)
    if run.quote_status == "draft":
        run.quote_status = "in_review"
    return run


class Approval(BaseModel):
    by: str = "specialist"


@app.post("/api/rfq/{rfq_id}/approve")
def approve(rfq_id: str, approval: Approval | None = None) -> Run:
    """Approve the quote as it stands: complete, or partial when lines are still open."""
    run = _run(rfq_id)
    if run.leak_check is None or not run.leak_check.passed:
        raise HTTPException(409, "The leak check failed, so this quote cannot be approved: "
                            + "; ".join(run.leak_check.hits if run.leak_check else ["not run"]))
    run.quote_status = "approved"
    run.approved_by = f"{(approval or Approval()).by} at {datetime.now().astimezone():%Y-%m-%d %H:%M %Z}"
    return run


@app.get("/api/rfq/{rfq_id}/trace")
def get_trace(rfq_id: str) -> pipeline.Trace:
    _run(rfq_id)
    return RUNS[rfq_id].trace


@app.get("/api/rfq/{rfq_id}/summary", response_class=PlainTextResponse)
def summary(rfq_id: str) -> str:
    return render.internal_summary(_run(rfq_id))


@app.get("/quote/{rfq_id}", response_class=HTMLResponse)
def quote(rfq_id: str) -> str:
    return render.quote_html(_run(rfq_id))


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    page = ROOT / "static" / "index.html"
    if page.exists():
        return page.read_text()
    return ("<p>The review screen (task 15) is not built yet. The API is running: "
            "<a href=\"/docs\">/docs</a>.</p>")
