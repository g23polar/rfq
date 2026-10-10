"""Live check of the Nicrron gateway. Run: uv run python scripts/smoke_nicrron.py

Sends one real request per model through rfq.llm (bypassing the local cache), and probes
whether each model accepts `temperature`, so MODEL_OPTIONS in llm.py stays true.
"""
import os
import sys

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel

from rfq.llm import BASE_URL, MODEL_FAST, MODEL_OPTIONS, MODEL_READ, ModelCallError, call_json


class Probe(BaseModel):
    grade: str
    gauge: int


load_dotenv(".env")
if not os.environ.get("NICRRON_API_KEY"):
    sys.exit("NICRRON_API_KEY is not set in .env")
os.environ["RFQ_LLM_NO_CACHE"] = "1"

failed = False
for model in (MODEL_READ, MODEL_FAST):
    try:
        result = call_json("Read the metal grade and gauge from the line.", "304 SS sheet 16ga",
                           Probe, model=model)
        call = result.calls[-1]
        print(f"OK   {model}: {result.value.model_dump()} in {call.latency_ms} ms, "
              f"{call.tokens_in}+{call.tokens_out} tokens, {len(result.calls)} attempt(s)")
    except ModelCallError as e:
        failed = True
        print(f"FAIL {model}: {e}")

client = OpenAI(base_url=BASE_URL, api_key=os.environ["NICRRON_API_KEY"], timeout=30)
for model in (MODEL_READ, MODEL_FAST):
    try:
        client.chat.completions.create(model=model, max_tokens=5, temperature=0,
                                       messages=[{"role": "user", "content": "Say ok."}])
        accepts = True
    except Exception:
        accepts = False
    configured = "temperature" in MODEL_OPTIONS[model]
    note = "" if accepts == configured else "  <-- MODEL_OPTIONS in llm.py disagrees"
    failed = failed or (configured and not accepts)
    print(f"temperature {'accepted' if accepts else 'rejected'} by {model}{note}")

sys.exit(1 if failed else 0)
