from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from rfq import app as app_module
from rfq.models import LeakCheck

ROOT = Path(__file__).parent.parent


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("RFQ_LLM_CACHE", str(ROOT / "tests" / "recordings"))
    monkeypatch.setattr(app_module, "_recorder", lambda: None)
    app_module.RUNS.clear()
    return TestClient(app_module.app)


def test_sample_to_approved_quote(client):
    assert client.get("/api/samples").json() == {"email": "rfq_email.txt", "pdf": "rfq.pdf"}
    run = client.post("/api/samples/email").json()
    rfq_id = run["rfq_id"]
    assert run["quote_status"] == "draft" and len(run["lines"]) == 7
    assert run["lines"][0]["offers"][0]["price"]["cost_per_lb"] > 0  # the specialist sees cost

    assert client.get(f"/api/rfq/{rfq_id}").json()["quote_status"] == "in_review"
    page = client.get(f"/quote/{rfq_id}").text
    assert "DRAFT" in page and "cost_per_lb" not in page

    approved = client.post(f"/api/rfq/{rfq_id}/approve", json={"by": "Dana"}).json()
    assert approved["quote_status"] == "approved" and approved["approved_by"].startswith("Dana at ")
    assert approved["completeness"] == "partial"
    assert "DRAFT" not in client.get(f"/quote/{rfq_id}").text
    assert "not for the buyer" in client.get(f"/api/rfq/{rfq_id}/summary").text
    assert client.get(f"/api/rfq/{rfq_id}/trace").json()["spans"]


def test_upload_and_pasted_text(client):
    with open(ROOT / "fixtures" / "rfq_email.txt", "rb") as f:
        uploaded = client.post("/api/rfq", files={"file": ("rfq_email.txt", f, "text/plain")})
    assert uploaded.status_code == 200 and uploaded.json()["source"]["kind"] == "email"
    pasted = client.post("/api/rfq", data={"text": (ROOT / "fixtures" / "rfq_email.txt").read_text()})
    assert pasted.json()["rfq_id"] == uploaded.json()["rfq_id"]
    assert client.post("/api/rfq", data={"text": "  "}).status_code == 400


def test_approval_is_refused_when_the_leak_check_failed(client):
    rfq_id = client.post("/api/samples/email").json()["rfq_id"]
    app_module.RUNS[rfq_id].run.leak_check = LeakCheck(passed=False, hits=["cost 1.73 in quote"])
    refused = client.post(f"/api/rfq/{rfq_id}/approve")
    assert refused.status_code == 409 and "cost 1.73" in refused.json()["detail"]
    assert client.get(f"/api/rfq/{rfq_id}").json()["quote_status"] != "approved"


def test_unknown_run_and_sample(client):
    assert client.get("/api/rfq/Q-NOPE").status_code == 404
    assert client.get("/quote/Q-NOPE").status_code == 404
    assert client.post("/api/samples/nope").status_code == 404
    assert client.get("/").status_code == 200
