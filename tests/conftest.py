import pytest

# Set by a developer's .env, which `rfq.app` loads on import. Tests must behave the same
# whatever is in it, and must never reach Nicrron or PRISM.
ENV_FROM_DOTENV = ("NICRRON_API_KEY", "PRISMTRACE_API_KEY", "PRISMTRACE_PROJECT_ID",
                   "RFQ_JURY_MODEL", "RFQ_LLM_NO_CACHE")


@pytest.fixture(autouse=True)
def no_network(monkeypatch, tmp_path):
    """No keys, no optional second model, and a private, empty response cache. A test that
    needs one of these sets it itself."""
    for name in ENV_FROM_DOTENV:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("RFQ_LLM_CACHE", str(tmp_path / "llm"))
