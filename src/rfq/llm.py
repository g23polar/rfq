"""Model access through the Nicrron gateway (plans/07-model-client.md).

One entry point, `call_json`: send a prompt, get back a validated instance of a pydantic
shape, or a `ModelCallError`. Every response is saved to a local cache keyed by the exact
request, so the same RFQ always gets the same reading and tests run with no network.
"""

import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, ValidationError

BASE_URL = "https://api.nicrron.ai/v1"
MODEL_READ = "anthropic/claude-sonnet-5"  # segmentation and interpretation
MODEL_FAST = "anthropic/claude-haiku-4-5"  # safety screen and question wording
# Request options each model accepts through Nicrron, as found by scripts/smoke_nicrron.py.
# claude-sonnet-5 rejects `temperature`, so repeatability for it comes from the local cache.
MODEL_OPTIONS: dict[str, dict] = {MODEL_READ: {}, MODEL_FAST: {"temperature": 0}}
MAX_TOKENS = 2000
TIMEOUT_S = 60

T = TypeVar("T", bound=BaseModel)


class CallRecord(BaseModel):
    """One request to the model, kept so PRISM recording can replay it (task 13)."""

    model: str
    messages: list[dict[str, str]]
    output: str
    tokens_in: int = 0
    tokens_out: int = 0
    latency_ms: int = 0
    source: Literal["live", "cache"]
    attempt: int


@dataclass
class ModelResult(Generic[T]):
    value: T
    calls: list[CallRecord] = field(default_factory=list)


class ModelCallError(Exception):
    """The model could not be reached or did not return valid JSON after one retry."""

    def __init__(self, message: str, calls: list[CallRecord] | None = None):
        super().__init__(message)
        self.calls = calls or []


def _cache_dir() -> Path:
    return Path(os.environ.get("RFQ_LLM_CACHE", ".cache/llm"))


def _cache_path(model: str, messages: list[dict[str, str]]) -> Path:
    digest = hashlib.sha256(json.dumps([model, messages], sort_keys=True).encode()).hexdigest()
    return _cache_dir() / f"{digest[:24]}.json"


def _send(model: str, messages: list[dict[str, str]], options: dict) -> tuple[str, int, int]:
    """The only function that touches the network."""
    from openai import OpenAI

    client = OpenAI(base_url=BASE_URL, api_key=os.environ["NICRRON_API_KEY"], timeout=TIMEOUT_S)
    response = client.chat.completions.create(model=model, messages=messages,
                                              max_tokens=MAX_TOKENS, **options)
    usage = response.usage
    return (response.choices[0].message.content or "",
            usage.prompt_tokens if usage else 0, usage.completion_tokens if usage else 0)


def _complete(model: str, messages: list[dict[str, str]], attempt: int) -> CallRecord:
    path = _cache_path(model, messages)
    if path.exists() and not os.environ.get("RFQ_LLM_NO_CACHE"):
        saved = json.loads(path.read_text())
        return CallRecord(model=model, messages=messages, output=saved["output"],
                          tokens_in=saved["tokens_in"], tokens_out=saved["tokens_out"],
                          source="cache", attempt=attempt)
    if not os.environ.get("NICRRON_API_KEY"):
        raise ModelCallError(f"NICRRON_API_KEY is not set and no saved response exists in "
                             f"{_cache_dir()} for this request.")
    started = time.monotonic()
    try:
        output, tokens_in, tokens_out = _send(model, messages, MODEL_OPTIONS.get(model, {}))
    except Exception as e:  # the SDK has already retried transient failures
        raise ModelCallError(f"Nicrron request failed for {model}: {e}") from e
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"model": model, "output": output, "tokens_in": tokens_in,
                                "tokens_out": tokens_out}, indent=1))
    return CallRecord(model=model, messages=messages, output=output, tokens_in=tokens_in,
                      tokens_out=tokens_out, latency_ms=int((time.monotonic() - started) * 1000),
                      source="live", attempt=attempt)


def _extract_json(text: str) -> str:
    """The JSON object in a reply; models often wrap it in a code fence."""
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("reply contains no JSON object")
    return text[start:end + 1]


def call_json(system: str, user: str, shape: type[T], model: str = MODEL_READ) -> ModelResult[T]:
    """Ask the model for JSON matching `shape`. One retry, with the validation error, if it
    doesn't; then `ModelCallError`."""
    schema = json.dumps(shape.model_json_schema())
    messages = [
        {"role": "system", "content": f"{system}\n\nReply with one JSON object that matches "
                                      f"this JSON Schema, and nothing else:\n{schema}"},
        {"role": "user", "content": user},
    ]
    calls: list[CallRecord] = []
    error: Exception | None = None
    for attempt in (1, 2):
        try:
            record = _complete(model, messages, attempt)
        except ModelCallError as e:
            raise ModelCallError(str(e), calls) from e
        calls.append(record)
        try:
            return ModelResult(shape.model_validate_json(_extract_json(record.output)), calls)
        except (ValidationError, ValueError) as e:
            error = e
            messages = messages + [
                {"role": "assistant", "content": record.output},
                {"role": "user", "content": f"That reply was not valid: {str(e)[:1500]}\n"
                                            f"Reply again with only the corrected JSON object."},
            ]
    raise ModelCallError(f"{model} did not return valid {shape.__name__} JSON after one retry: "
                         f"{error}", calls)
