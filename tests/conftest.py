import pytest


@pytest.fixture(autouse=True)
def no_network(monkeypatch, tmp_path):
    """Tests never reach Nicrron: no key, and a private, empty response cache."""
    monkeypatch.delenv("NICRRON_API_KEY", raising=False)
    monkeypatch.delenv("RFQ_LLM_NO_CACHE", raising=False)
    monkeypatch.setenv("RFQ_LLM_CACHE", str(tmp_path / "llm"))
